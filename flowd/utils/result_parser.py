import os
import pandas as pd
import matplotlib.pyplot as plt


if __name__ == '__main__':
    collected_data_path = os.path.expanduser("~/flowd/")
    result_file = os.path.join(collected_data_path, "data.csv")

    result_data = {}
    date_times = []

    with open(result_file) as f:
        for line in f:
            metric_name, value, ts = line.strip('\n').split(',')

            if metric_name == 'test_metric':
                # filter test_metric
                continue

            if metric_name not in result_data:
                result_data[metric_name] = []

            date_times.append(ts)
            result_data[metric_name].append(float(value))

    deduplicate_date_times = list(dict.fromkeys(date_times))
    result_data['dates'] = deduplicate_date_times

    length_data = min(map(lambda item: len(item), result_data.values()))

    # set same length
    for key, values in result_data.items():
        result_data[key] = values[:length_data]

    df = pd.DataFrame(data=result_data)
    df.to_csv('data_.csv')
    df['dates'] = pd.to_datetime(df['dates'], infer_datetime_format=True)

    df.plot(x='dates', y=['activity_window', 'afk'])
    plt.show()
