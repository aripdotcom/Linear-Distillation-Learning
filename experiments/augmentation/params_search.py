import os
from time import time
import itertools
import numpy as np
import pandas as pd
import torch
from torch import nn

from train import run_experiment


if __name__ == "__main__":
    np.random.seed(2019)
    torch.manual_seed(2019)
    print("GPU available: ", torch.cuda.is_available())

    configs = {
        'dataset': ['omniglot'],
        'way': [3, 5, 10],
        'epochs': [10],
        'train_shot': [1, 3, 5, 10],
        'test_shot': [1],
        # ATTENTION: Due to the cached nature of dataloader this parameter should be set in signle value per run
        'x_dim': [28],
        'z_dim': [784, 2000],
        'optimizer': ['adam'],
        'lr': [0.001],
        'initialization': ['xavier_normal'],
        'channels': [1],
        'loss': [nn.MSELoss(reduction='none')],
        'trials': [100],
        'silent': [True],
        'split': ['test'],
        'in_alphabet': [False],
        'add_rotations': [True],
        'gpu': [0]
    }

    # Create grid of parameters
    keys, values = zip(*configs.items())
    param_grid = [dict(zip(keys, v)) for v in itertools.product(*values)]

    # Create resulting file if necessary
    ds_name = configs['dataset'][0]
    res_path = f"did/experiments/augmentation/{ds_name}_augmeted.csv"
    if not os.path.exists(res_path):
        df = pd.DataFrame(columns=configs.keys())
        df.to_csv(res_path, index=False)

    conf_durations = []
    for i, param in enumerate(param_grid):
        if len(conf_durations):
            time_estimate = (len(param_grid) - (i+1)) * np.mean(conf_durations) // 60
        else:
            time_estimate = '-'
        print(f"Configuration: {i+1}/{len(param_grid)}. Estimated time until end: {time_estimate} min")
        time_start = time()
        mean_accuracy = run_experiment(config=param)
        conf_durations.append(time() - time_start)
        df = pd.read_csv(res_path)
        df = df.append(pd.Series({**param, **{'accuracy': mean_accuracy, 'duration_sec': conf_durations[-1]}}), ignore_index=True)
        df.to_csv(res_path, index=False)

