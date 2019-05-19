import os
from time import time
import itertools
import numpy as np
import pandas as pd
import torch
from torch import nn

from train import run_experiment_full_test


if __name__ == "__main__":
    print("GPU available: ", torch.cuda.is_available())

    configs = {
        'dataset': ['mnist'],
        'way': [10],
        'train_shot': [1, 10, 50, 200, 300],
        'test_shot': [1],
        'loss': [nn.MSELoss(reduction='none')],
        'epochs': [3, 10],
        'trials': [50],
        'silent': [True],
        'split': ['test'],
        'x_dim': [28],
        'z_dim': [784, 2000],
        'lr_predictor': [1e-3, 1e-4, 1e-5],
        'lr_target': [1e-3, 1e-4],
        'channels': [1],
        'gpu': [0],
        'test_batch': [2000],
        'save_data': [False]
    }

    # Create grid of parameters
    keys, values = zip(*configs.items())
    param_grid = [dict(zip(keys, v)) for v in itertools.product(*values)]

    # Create resulting file if necessary
    res_path = "did/experiments/ldl/results_mnist.csv"
    if not os.path.exists(res_path):
        df = pd.DataFrame(columns=configs.keys())
        df.to_csv(res_path, index=False)

    conf_durations = []
    for i, param in enumerate(param_grid):
        if len(conf_durations):
            time_estimate = (len(param_grid) - (i+1)) * np.mean(conf_durations) // 60
        else:
            time_estimate = '-'
        print(f"Configuration: ", param)
        print(f"Progress {i+1}/{len(param_grid)}. Estimated time until end: {time_estimate} min")
        time_start = time()
        mean_accuracy = run_experiment_full_test(config=param)
        conf_durations.append(time() - time_start)
        df = pd.read_csv(res_path)
        df = df.append(pd.Series({**param, **{'accuracy': mean_accuracy,
                                              'duration_sec': conf_durations[-1]}}), ignore_index=True)
        df.to_csv(res_path, index=False)
