import pandas as pd
import numpy as np
from scipy.signal import find_peaks

class SupportResistance:
    import pandas as pd
import numpy as np

class SupportResistance:
    def _find_peaks(self, prices, prominence=None, distance=None):
        """Finds local peaks using scipy.signal.find_peaks."""
        peaks, _ = find_peaks(prices, prominence=prominence, distance=distance)
        return peaks

    def _find_troughs(self, prices, prominence=None, distance=None):
        """Finds local troughs by finding peaks in the inverted prices."""
        troughs, _ = find_peaks(-prices, prominence=prominence, distance=distance)
        return troughs

    def _get_n_most_recent_prominent(self, indices, prices, n=2):
        """Gets the indices of the n most recent prominent peaks or troughs."""
        if not indices.size:
            return np.array([])
        # Sort indices by time (which is the index itself in our case) in descending order
        sorted_indices_by_time = np.sort(indices)[::-1]
        return sorted_indices_by_time[:n]

    def _get_line(self, index1, price1, index2, price2, length):
        """Calculates the line equation (y = mx + c)."""
        if index1 == index2:
            return np.full(length, price1)  # Horizontal line
        slope = (price2 - price1) / (index2 - index1)
        intercept = price1 - slope * index1
        return slope * np.arange(length) + intercept

    def support_resistance_trend_lines(self, data, lookback=20, prominence=None, distance=None):
        if data is None or len(data) < lookback:
            return pd.DataFrame()
        try:
            recent_data = data.iloc[-lookback:].copy()
            high_prices = recent_data['high'].values
            low_prices = recent_data['low'].values
            ts = recent_data['time'].values

            # Find all local peaks and troughs
            peak_indices_all = self._find_peaks(high_prices, prominence=prominence, distance=distance)
            if len(peak_indices_all) > 0 and peak_indices_all[-1] < lookback - 2 and high_prices[-2] >  high_prices[lookback - peak_indices_all[-1]]:
                peak_indices_all = np.append(peak_indices_all,lookback - 2)
            trough_indices_all = self._find_troughs(low_prices, prominence=prominence, distance=distance)
            if len(trough_indices_all) > 0 and trough_indices_all[-1] < lookback - 2 and low_prices[-2] < low_prices[lookback - trough_indices_all[-1]]:
                trough_indices_all = np.append(trough_indices_all, lookback - 2)
            # Get the two most recent prominent peaks
            most_recent_peaks_indices = self._get_n_most_recent_prominent(peak_indices_all, high_prices, n=2)

            # Get the two most recent prominent troughs
            most_recent_troughs_indices = self._get_n_most_recent_prominent(trough_indices_all, low_prices, n=2)

            support_line = np.full(lookback, np.nan)
            resistance_line = np.full(lookback, np.nan)

            if len(most_recent_peaks_indices) >= 2:
                # Sort by index (time) to ensure correct order
                sorted_peak_indices = most_recent_peaks_indices #np.sort(most_recent_peaks_indices)
                resistance_line_full = self._get_line(sorted_peak_indices[0], high_prices[sorted_peak_indices[0]],
                                                      sorted_peak_indices[1], high_prices[sorted_peak_indices[1]], lookback)
                # Set values before the second peak to NaN
                resistance_line[sorted_peak_indices[1]:] = resistance_line_full[sorted_peak_indices[1]:]
            elif len(most_recent_peaks_indices) == 1:
                resistance_line[most_recent_peaks_indices[0]:] = high_prices[most_recent_peaks_indices[0]] # Horizontal line from the peak onwards

            if len(most_recent_troughs_indices) >= 2:
                # Sort by index (time) to ensure correct order
                sorted_trough_indices = most_recent_troughs_indices #np.sort(most_recent_troughs_indices)
                support_line_full = self._get_line(sorted_trough_indices[0], low_prices[sorted_trough_indices[0]],
                                                   sorted_trough_indices[1], low_prices[sorted_trough_indices[1]], lookback)
                # Set values before the second trough to NaN
                support_line[sorted_trough_indices[1]:] = support_line_full[sorted_trough_indices[1]:]
            elif len(most_recent_troughs_indices) == 1:
                support_line[most_recent_troughs_indices[0]:] = low_prices[most_recent_troughs_indices[0]] # Horizontal line from the trough onwards

            results_df = pd.DataFrame({
                'time': ts,
                'support_line': support_line,
                'resistance_line': resistance_line
            })
            return results_df
        except Exception as e:
            print(f"An error occurred: {e}")
            return pd.DataFrame()