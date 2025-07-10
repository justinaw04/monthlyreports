# app.py
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
import os
import zipfile
import io
import tempfile
import shutil
import datetime

app = Flask(__name__)
# Set a secret key for flashing messages (can be any random string)
app.secret_key = 'super_secret_key_for_flash_messages' 

@app.route('/')
def index():
    """Renders the main HTML page for file upload."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles the CSV file upload, processing, and zipping."""
    if 'csv_file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('index'))

    file = request.files['csv_file']

    if file.filename == '':
        flash('No selected file.', 'error')
        return redirect(url_for('index'))

    if file and file.filename.endswith('.csv'):
        # Create a temporary directory to store individual CSVs
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            print(f"Created temporary directory: {temp_dir}")

            # Read the CSV file into a pandas DataFrame
            # Using io.StringIO to read the file content as a string
            csv_content = io.StringIO(file.read().decode('utf-8'))
            df = pd.read_csv(csv_content)

            development_column = "Development Name??"

            # Check if the development column exists
            if development_column not in df.columns:
                flash(f"Error: Column '{development_column}' not found in the CSV file. Please ensure the header is correct.", 'error')
                return redirect(url_for('index'))

            # Drop rows where 'Development Name??' is NaN (empty) before getting unique names
            unique_developments = df[development_column].dropna().unique()

            if len(unique_developments) == 0:
                flash(f"No unique development names found in the column '{development_column}'. No reports generated.", 'warning')
                return redirect(url_for('index'))

            print(f"Found {len(unique_developments)} unique development names.")

            # Get all original headers to ensure consistent columns in output files
            all_headers = df.columns.tolist()

            # Iterate through unique development names and save separate CSVs
            for dev_name in unique_developments:
                # Sanitize development name for filename
                # Replace problematic characters and strip whitespace
                safe_dev_name = str(dev_name).replace('/', '_').replace('\\', '_').replace('?', '').replace(':', '_').replace('*', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '').strip()
                
                if not safe_dev_name:
                    print(f"Skipping a development with an unprocessable name: '{dev_name}'")
                    continue

                # Filter the DataFrame for the current development name
                development_df = df[df[development_column] == dev_name]

                # Construct the output filename within the temporary directory
                output_filename = os.path.join(temp_dir, f"{safe_dev_name}_Report.csv")

                # Save the filtered data to a new CSV file
                # Use index=False to prevent pandas from writing the DataFrame index as a column
                development_df.to_csv(output_filename, index=False, encoding='utf-8')
                print(f"Created: {output_filename} with {len(development_df)} rows.")

            # Create an in-memory zip file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(temp_dir):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        # Add file to zip, preserving directory structure within the zip
                        # Arcname ensures the files are directly in 'Monthly_Reports/' inside the zip
                        zf.write(file_path, os.path.join('Monthly_Reports', file_name))
            zip_buffer.seek(0) # Rewind the buffer to the beginning

            # Generate a dynamic zip file name
            current_date = datetime.datetime.now()
            zip_filename = f"Monthly_Reports_{current_date.strftime('%Y-%m')}.zip"

            # Send the zip file as a response
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )

        except Exception as e:
            print(f"An error occurred during processing: {e}")
            flash(f'An error occurred during processing: {e}', 'error')
            return redirect(url_for('index'))
        finally:
            # Clean up the temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # When running locally, Flask will use a default port (e.g., 5000)
    # For Render, it will use the PORT environment variable
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))

