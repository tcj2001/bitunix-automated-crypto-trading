import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import talib

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

    def support_resistance_trend_lines(self, data, lookback=24, prominence=None, distance=None):
        if data is None or len(data) < lookback:
            return pd.DataFrame()
        try:
            recent_data = data.iloc[-lookback:].copy()
            high_prices = recent_data['high'].values
            low_prices = recent_data['low'].values
            ts = recent_data['time'].values

            # Find all local peaks and troughs
            peak_indices_all = self._find_peaks(high_prices, prominence=prominence, distance=distance)
            trough_indices_all = self._find_troughs(low_prices, prominence=prominence, distance=distance)

            support_line = np.full(lookback, np.nan)
            resistance_line = np.full(lookback, np.nan)

            if len(peak_indices_all) > 0:
                if len(peak_indices_all) >= 2:
                    resistance_line_full = self._get_line(peak_indices_all[-1], high_prices[peak_indices_all[-1]],
                                                        peak_indices_all[-2], high_prices[peak_indices_all[-2]], lookback)
                    # Set values before the second peak to NaN
                    resistance_line[peak_indices_all[-2]:] = resistance_line_full[peak_indices_all[-2]:]
                elif len(peak_indices_all) == 1:
                    resistance_line[peak_indices_all[-1]:] = high_prices[peak_indices_all[-1]] # Horizontal line from the peak onwards

            if len(trough_indices_all) > 0:
                if len(trough_indices_all) >= 2:
                    support_line_full = self._get_line(trough_indices_all[-1], low_prices[trough_indices_all[-1]],
                                                    trough_indices_all[-2], low_prices[trough_indices_all[-2]], lookback)
                    # Set values before the second trough to NaN
                    support_line[trough_indices_all[-2]:] = support_line_full[trough_indices_all[-2]:]
                elif len(trough_indices_all) == 1:
                    support_line[trough_indices_all[-1]:] = low_prices[trough_indices_all[-1]] # Horizontal line from the trough onwards

            results_df = pd.DataFrame({
                'time': ts,
                'support_line': support_line,
                'resistance_line': resistance_line
            })
            return results_df
        except Exception as e:
            print(f"trendline error occurred: {e}")
            return pd.DataFrame()
        
    def support_resistance_bos_lines(self, data, length, lookback=24):
        if data is None or len(data) < lookback:
            return pd.DataFrame()
        try:
            recent_data = data.iloc[-length:].copy()
            highs = recent_data['high'].values
            high_prices = np.full_like(highs, np.nan, dtype=np.float64)
            high_prices[-lookback:] = highs[-lookback:]
            
            lows = recent_data['low'].values
            low_prices = np.full_like(lows, np.nan, dtype=np.float64)
            low_prices[-lookback:] = lows[-lookback:]

            ts = recent_data['time'].values

            support_line = np.full(length, np.nan)
            resistance_line = np.full(length, np.nan)

            # Find all local peaks and troughs and its highest and lowest values
            peak_indices_all = self._find_peaks(high_prices)
            if len(peak_indices_all) == 0:
                highest_peak_index = peak_indices_all[np.argmax(high_prices[peak_indices_all])]
                highest_peak_value = high_prices[highest_peak_index]
                resistance_line[highest_peak_index:] = high_prices[highest_peak_index] # Horizontal line from the highest point onwards

            trough_indices_all = self._find_troughs(low_prices)
            if len(trough_indices_all) == 0:
                lowest_peak_index = trough_indices_all[np.argmin(low_prices[trough_indices_all])]
                lowest_peak_value = low_prices[lowest_peak_index]
                support_line[lowest_peak_index:] = low_prices[lowest_peak_index] # Horizontal line from the lowset point onwards

            results_df = pd.DataFrame({
                'time': ts,
                'support_line': support_line,
                'resistance_line': resistance_line
            })
            return results_df
        except Exception as e:
            print(f"bos error occurred: {e}")
            return pd.DataFrame()

