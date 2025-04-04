import os

# Clear all environment variables
for key in list(os.environ.keys()):
    del os.environ[key]

# Verify that all environment variables are cleared
print(os.environ)