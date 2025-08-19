# Steps

1. Go to tower_demo directory
    ```
    cd tower_demo
    ```
2. create & activate venv 
    ```
    python -m venv venv
    source venv/bin/activate
    ```
3. install dependencies in your venv by running
    ```
    pip install -r requirements.txt
    ```
4. when you need to update dependencies in your requirements.txt, update the pyproject.toml file, then run 
    ```
    uv export --format=requirements-txt --no-hashes > requirements.txt 
    ```
5. run the python script for test from the tower_demo directory
    ```
    python task.py
    ```

## Tower setup

1. After installing requirements (including Tower), you need to login tower by running: 
    ```
    tower login 
    ```
    You will be prompted to tower UI. Please complete login.

2. You will use Tower CLI to deploy and run your app 
    ```
    tower deploy 
    ```
    ```
    tower run       
    # run `tower run --local` if you want to run locally
    ```
    
> This demo uses Iceberg with Snowflake Open Catalog and S3. 
> Follow the Tower [blog series](https://tower.dev/blog/how-to-create-s3-buckets-to-store-your-lakehouse-data-and-metadata) to complete the setup.