import pandas as pd
from jinja2 import Template

class DataFrameHtmlRenderer:
    def __init__(self, hide_columns=None, color_column_mapping=None):
        """
        Initialize the renderer with columns to hide and column-color mapping.
        """
        self.hide_columns = hide_columns or []
        self.color_column_mapping = color_column_mapping or {}

    def preprocess_styles(self, dataframe):
        """
        Precomputes the styles for columns that need coloring based on the provided DataFrame.
        Returns a DataFrame with styles.
        """
        style_df = pd.DataFrame(index=dataframe.index, columns=dataframe.columns)
        for col, color_col in self.color_column_mapping.items():
            if col in dataframe.columns and color_col in dataframe.columns:
                style_df[col] = dataframe[color_col]  # Copy the color values
        return style_df.fillna("")  # Fill empty cells with blank strings

    def render_html(self, dataframe):
        """
        Renders the DataFrame as an HTML string with conditional coloring for specified columns.
        """
        style_df = self.preprocess_styles(dataframe)

        # Create combined_data for all columns
        combined_data = []
        for index, row in dataframe.iterrows():
            row_data = []
            for col in dataframe.columns:
                row_data.append({
                    "value": row[col],        # The cell's value
                    "style": style_df.at[index, col],  # The cell's style (if any)
                    "column": col            # The column name for the cell
                })
            combined_data.append(row_data)

        # Jinja2 HTML template
        template = Template("""
        <table border="1" style="border-collapse: collapse; width: 100%; font-size: small;"> 
        <thead>
                <tr>
                    {% for column in columns if column not in hide_columns %}
                    <th>{{ column }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for row in combined_data %}
                <tr>
                    {% for cell in row %}
                    {% if cell.column not in hide_columns %}
                    <td {% if cell.style %} style="background-color: {{ cell.style }};" {% endif %}>
                        {{ cell.value }}
                    </td>
                    {% endif %}
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        """)

        # Render the HTML
        html_output = template.render(
            columns=dataframe.columns.tolist(),  # All columns
            hide_columns=self.hide_columns,      # Columns to hide
            combined_data=combined_data          # Combined data (values + styles)
        )
        return html_output

