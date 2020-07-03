import pandas as pd

import os
import logging

import torch
from torch import nn, optim

import math
import numpy as np
import math
import time
from sklearn.metrics import roc_auc_score

from flowd.utils import wnf


data_path = os.path.expanduser("~/flowd/")
metrics = [
    "Active Window Changed (times)",
    "Any Shortcut Used (times)",
    "Code Assist Activated (times)",
    "Distraction Class Window Activated (times)",
    "Full Lines Entered (times)",
    "Mouse Used (seconds)",
    "Mouse Used for Selection (times)",
    "Popular Shortcuts Used (times)",
    "Productivity Class Window Activated (times)",
    "SSH Session Active (seconds)",
    "Test Metric",
    "Time in AFK (seconds)",
    "Time in Alerts Only Mode (seconds)",
    "Time in Priority Mode (seconds)",
    "Voice Activity Detected (seconds)"
]

fs_col = "Flow State"

epochs = 1000
learning_rate = 0.001


class LogisticRegressionTorch(nn.Module):
    def __init__(self, input_size, output_size):
        super(LogisticRegressionTorch, self).__init__()
        self.linear = nn.Linear(input_size, output_size)

    def forward(self, x):
        return torch.sigmoid(self.linear(x))


def load_train_data() -> tuple:
    df_state = pd.read_csv(f'{data_path}/.data_pivot.csv')
    df_state.dropna(inplace=True)
    x = df_state[metrics]
    y = df_state[fs_col]
    return x, y


def train_model() -> LogisticRegressionTorch:
    x, y = load_train_data()
    x_tensor = torch.from_numpy(x.values).float()
    y_tensor = torch.from_numpy(y.values.reshape(-1, 1)).float()

    model = LogisticRegressionTorch(x_tensor.shape[1], y_tensor.shape[1])
    # определяем функцию потерь — бинарную кросс-энтропию
    criterion = nn.BCELoss()
    # определяем алгоритм оптимизации Adam
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    for epoch in range(epochs):
        optimizer.zero_grad()
        t_predictions = model(x_tensor)
        loss = criterion(t_predictions, y_tensor)
        # вычисляем градиенты
        loss.backward()
        # обновляем параметры
        optimizer.step()

    return model


def measure_model(model, x_tensor, y):
    return roc_auc_score(y, model(x_tensor).detach().numpy())


def pivot_stats():
    df_metric = pd.read_csv(f'{data_path}/data.csv')
    df_pivot = pd.pivot_table(df_metric, values=['Value'], index=['date'], columns=['Metric'], fill_value=0)
    p = f'{data_path}/data_pivot.csv'
    df_pivot.to_csv(p, header=metrics)
    return p


def predict(path, model, mins):
    df = pd.read_csv(path, index_col=False, infer_datetime_format=True, keep_date_col=True, parse_dates=[0])
    x = df[metrics]
    x_tensor = torch.from_numpy(x.values).float()
    predictions = model(x_tensor)
    fs_last_mins = predictions.detach().numpy()[-mins:].mean()
    return fs_last_mins

    # y = df_state2[fs_col]
    # y_tensor = torch.from_numpy(y.values.reshape(-1, 1)).float()
    # print(f'Model score: {roc_auc_score(y, predictions.detach().numpy())}')

    # df = pd.DataFrame(list(zip(
    #     [pd.to_datetime(ts) for ts in df['date']], predictions.detach().numpy().squeeze())),
    #     columns=['Date/Time', 'Prediction'])
    # sns.set(rc={'figure.figsize': (21, 6)})
    # df.set_index('Date/Time', inplace=True)
    # df['Prediction'].plot()


if __name__ == "__main__":
    # Example of usage
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    model = train_model()
    while True:
        p = int(predict(pivot_stats(), model, 15) * 100)
        logging.info(f'Last 15 minutes prediction {p}%')
        if p > 70:
            wnf.set_focus_mode(2)
        else:
            wnf.set_focus_mode(0)
        time.sleep(60)
