conda env create -f environment.yml
source activate chemprop_predict
python predict.py --test_path data/tox21.csv --checkpoint_dir tox21_checkpoints --preds_path tox21_preds.csv