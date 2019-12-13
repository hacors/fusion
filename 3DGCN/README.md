# 3DGCN: Three-Dimensionally Embedded Graph Convolutional Network

This is a implementation of our paper "Three-Dimensionally Embedded Graph Convolutional Network for interpreting spatial topology of molecules":

Hyeoncheol Cho, Insung S. Choi, [Three-Dimensionally Embedded Graph Convolutional Network (3DGCN) for Molecule Interpretation](https://arxiv.org/abs/1811.09794)


## Requirements

* Tensorflow
* Keras
* RDKit

## Datasets
* FreeSolv
* ESOL (= delaney)
* BACE
* HIV

Note that bace and bace_rotated in the code correspond to BACE_algn and BACE on paper, respectively.

## Experiments

See the `experiment` folder for training and evaluation demos of a 3DGCN model on three datasets.

## Cite

If you use 3DGCN in your research, please cite:
```
@article{cho2018three,
  title={Three-Dimensionally Embedded Graph Convolutional Network (3DGCN) for Molecule Interpretation},
  author={Cho, Hyeoncheol and Choi, Insung},
  journal={arXiv preprint arXiv:1811.09794},
  year={2018}
}
```