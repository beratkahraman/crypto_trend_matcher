import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from fastdtw import fastdtw
import os
from datetime import datetime


class ChartAnalyzer:
    @staticmethod
    def normalize_data(data):
        """
        Z-Score Normalization kullanır.
        Formül: (Değer - Ortalama) / Standart Sapma
        Avantajı: Volatiliteyi korur. %1'lik hareket ile %20'lik hareketi ayırt eder.
        """
        arr = np.array(data, dtype=np.float64).flatten()
        if len(arr) < 2: return []

        mean = np.mean(arr)
        std = np.std(arr)

        if std == 0:
            return np.zeros_like(arr).tolist()

        return ((arr - mean) / std).tolist()

    def calculate_similarity(self, series_a, series_b):
        try:
            a = self.normalize_data(series_a)
            b = self.normalize_data(series_b)
            if not a or not b: return float('inf')
            distance, _ = fastdtw(a, b, dist=lambda x, y: abs(x - y))
            return distance
        except:
            return float('inf')

    def plot_comparison(self, target_name, target_data_full, match_name, match_data_now):
        try:
            plt.figure(figsize=(10, 6))

            target_norm = self.normalize_data(target_data_full['close'].values)
            plt.plot(target_norm, label=f"Emsal: {target_name}", color='orange', alpha=0.8, linestyle='--')

            match_norm = self.normalize_data(match_data_now['close'].values)
            plt.plot(range(len(match_norm)), match_norm, label=f"Sinyal: {match_name}", color='blue', linewidth=2)

            plt.title(f"Eşleşme Analizi: {match_name} vs {target_name}")
            plt.legend()
            plt.grid(True, alpha=0.3)

            if not os.path.exists("data/plots"):
                os.makedirs("data/plots")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"data/plots/{timestamp}_{match_name}.png"

            plt.savefig(file_path)
            plt.close()

            return file_path
        except Exception as e:
            print(f"Grafik çizim hatası: {e}")
            return None