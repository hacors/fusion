from keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from model.dataset import Dataset
from model import model as m
from model.callback import *
from datetime import datetime
import numpy as np
import time
import csv


class Trainer(object):
    def __init__(self, dataset):
        self.data = None
        self.model = None
        self.hyper = {"dataset": dataset}
        self.log = {}

    def __repr__(self):
        text = ""
        for key, value in self.log.items():
            text += "{}:\t".format(key)
            for error in value[0]:
                text += "{0:.4f} ".format(float(error))
            text += "\n"

        return text

    def load_data(self, batch=128):
        self.data = Dataset(self.hyper["dataset"], batch=batch)

        self.hyper["num_train"] = len(self.data.y["train"])
        self.hyper["num_val"] = len(self.data.y["valid"])
        self.hyper["num_test"] = len(self.data.y["test"])
        self.hyper["num_atoms"] = self.data.max_atoms
        self.hyper["num_features"] = self.data.num_features
        self.hyper["data_std"] = self.data.std
        self.hyper["data_mean"] = self.data.mean
        self.hyper["task"] = self.data.task
        self.hyper["outputs"] = self.data.outputs
        self.hyper["batch"] = batch

    def load_model(self, model, units_conv=128, units_dense=128, num_layers=2, loss="mse", pooling="max"):
        self.hyper["model"] = model
        self.hyper["units_conv"] = units_conv
        self.hyper["units_dense"] = units_dense
        self.hyper["num_layers"] = num_layers
        self.hyper["loss"] = loss
        self.hyper["pooling"] = pooling
        self.model = getattr(m, model)(self.hyper)
        self.model.summary()

    def fit(self, model, epoch, batch=128, fold=10, pooling="max", units_conv=128, units_dense=128, num_layers=2,
            loss="mse", monitor="val_rmse", mode="min", use_multiprocessing=True, label="", **kwargs):

        # 1. Generate CV folder
        now = datetime.now()
        base_path = "../../result/{}/{}/".format(model, self.hyper["dataset"])
        log_path = base_path
        results = []

        for i in range(1, fold + 1):
            start_time = time.time()

            # 2. Generate data
            self.load_data(batch=batch)
            self.data.set_features(**kwargs)
            self.hyper["num_features"] = self.data.num_features

            # 3. Make model
            self.load_model(model, units_conv=units_conv, units_dense=units_dense, num_layers=num_layers, loss=loss,
                            pooling=pooling)

            # 4. Callbacks
            log_path = base_path + "{}_c{}_d{}_l{}_p{}_{}{}/".format(batch, units_conv, units_dense, num_layers,
                                                                     pooling, label, now.strftime("%m%d%H"))
            tb_path = log_path + "trial_{}/".format(i)

            callbacks = []
            if self.data.task != "regression":
                callbacks.append(Roc(self.data.generator("valid")))
                mode = "max"
            callbacks += [Tensorboard(log_dir=tb_path, write_graph=False, histogram_freq=0, write_images=True),
                          ModelCheckpoint(tb_path + "{epoch:01d}-{" + monitor + ":.3f}.hdf5", monitor=monitor,
                                          save_weights_only=True, save_best_only=True, period=1, mode=mode),
                          EarlyStopping(patience=15, restore_best_weights=True),  # 15, hiv=10
                          ReduceLROnPlateau(monitor="val_loss", factor=0.9, patience=10, min_lr=0.0005)]

            # 5. Fit
            self.model.fit_generator(self.data.generator("train"), epochs=epoch,
                                     validation_data=self.data.generator("valid"), callbacks=callbacks,
                                     use_multiprocessing=use_multiprocessing, workers=6)
            self.model.save_weights(tb_path + "best_weight.hdf5")
            self.hyper["train_time"] = time.time() - start_time

            # 6. Save train, valid, test losses
            if self.data.task == "regression":
                train_loss = self.model.evaluate_generator(self.data.generator("train"),
                                                           use_multiprocessing=use_multiprocessing, workers=10)
                valid_loss = self.model.evaluate_generator(self.data.generator("valid"),
                                                           use_multiprocessing=use_multiprocessing, workers=10)
                test_loss = self.model.evaluate_generator(self.data.generator("test"),
                                                          use_multiprocessing=use_multiprocessing, workers=10)

                results.append([train_loss[1], valid_loss[1], test_loss[1], train_loss[2], valid_loss[2], test_loss[2]])

            else:
                losses = []
                for gen in [self.data.generator("train"), self.data.generator("valid"), self.data.generator("test")]:
                    val_roc, val_pr = calculate_roc_pr(self.model, gen)
                    losses.append(val_roc)
                    losses.append(val_pr)

                results.append([losses[0], losses[2], losses[4], losses[1], losses[3], losses[5]])

            # 7. Save hyper
            with open(tb_path + "hyper.csv", "w") as file:
                writer = csv.DictWriter(file, fieldnames=list(self.hyper.keys()))
                writer.writeheader()
                writer.writerow(self.hyper)

            # 8. Save data split and test results
            for target in ["train", "valid", "test"]:
                pred = self.model.predict_generator(self.data.generator(target, task="input_only"),
                                                    use_multiprocessing=use_multiprocessing, workers=10)
                self.data.save_dataset(tb_path, pred=pred, target=target)

        # 9. Save cross validation results
        if self.data.task == "regression":
            header = ["train_mae", "valid_mae", "test_mae", "train_rmse", "valid_rmse", "test_rmse"]
        else:
            header = ["train_roc", "valid_roc", "test_roc", "train_pr", "valid_pr", "test_pr"]

        with open(log_path + "raw_results.csv", "w") as file:
            writer = csv.writer(file, delimiter=",")
            writer.writerow(header)
            for r in results:
                writer.writerow(r)

        results = np.array(results)
        results = [np.mean(results, axis=0), np.std(results, axis=0)]
        with open(log_path + "results.csv", "w") as csvfile:
            writer = csv.writer(csvfile, delimiter=",")
            writer.writerow(header)
            for r in results:
                writer.writerow(r)

        # Update cross validation log
        self.log["{}_B{}_C{}_D{}_L{}_P{}".format(model, batch, units_conv, units_dense, num_layers, pooling,
                                                 )] = results

        print(self)
        print("Training Ended")
