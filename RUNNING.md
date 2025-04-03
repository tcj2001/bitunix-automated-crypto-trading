# Running the Bitunix Automated Crypto Trading Platform

After installing the package from PyPI, you can run it using the following steps:

## 1. Create a .env file

Create a `.env` file in your current directory with the following content:

```
API_KEY=your_api_key
SECRET_KEY=your_secret_key
SECRET=your_jwt_secret
PASSWORD=your_password
HOST=127.0.0.1
```

Replace the placeholder values with your actual Bitunix API credentials and desired settings.

## 2. Run the application

Simply run the command:

```
bitunixautotrade
```

This will start the Bitunix Automated Crypto Trading Platform with the settings from your `.env` file.

## 3. Access the web interface

Open your browser and navigate to:

```
http://127.0.0.1:8000
```

You should see the login page. Use the password you specified in the `.env` file to log in.

## Troubleshooting

If you encounter any issues:

1. Make sure TA-Lib is properly installed:
   ```
   python -c "import talib; print(talib.get_functions())"
   ```

2. Check that your `.env` file is in the correct directory and has the proper format

3. Verify that your Bitunix API credentials are correct

4. If the `bitunixautotrade` command is not found, make sure your Python scripts directory is in your PATH
