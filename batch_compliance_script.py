import tweepy
import requests
import time
import logging
import json
import argparse
import pandas as pd
import os
from datetime import datetime

# Replace with your actual Twitter API Bearer Token



LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
current_date = datetime.now().strftime('%Y-%m-%d')

log_filename = f"{os.path.basename(__file__)}_{current_date}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S', filemode='w')
BEARER_TOKEN = json.load(open('secrets.json'))['bt'] if os.path.exists('secrets.json') else None

# Initialize the Tweepy client
client = tweepy.Client(BEARER_TOKEN, wait_on_rate_limit=True)

def load_bearer_token():
    try:
        with open('secrets.json', 'r') as f:
            secrets = json.load(f)
            return secrets['bt']
    except FileNotFoundError:
        raise FileNotFoundError("secrets.json file not found")
    except KeyError:
        raise KeyError("The key 'bt' is not found in secrets.json")
    except json.JSONDecodeError:
        raise ValueError("secrets.json is not a valid JSON file")
    except Exception as e:
        raise e

def create_compliance_job(job_name, job_type):
    response = client.create_compliance_job(name=job_name, type=job_type)
    return response.data['upload_url'], response.data['download_url'], response.data['id']

def upload_dataset(upload_url, file_path):
    headers = {'Content-Type': "text/plain"}
    with open(file_path, 'rb') as file:
        response = requests.put(upload_url, data=file, headers=headers)
        if response.status_code != 200:
            raise Exception(response.status_code, response.text)
        return response.text

def get_compliance_job_status(job_id):
    job = client.get_compliance_job(id=job_id)
    return job.data['status']

def download_results(download_url):
    response = requests.get(download_url)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.text.splitlines()


def make_txt_files(debug=False):
    fr_file = "__MINIMAL_FRIENDS_10.06.2023__05.51.02__START0_END-1_merged.csv"
    logging.info("read from file")

    fr = pd.read_csv(fr_file, dtype={'main':'object', 'friends_id':'object'})
    ego_ids = list(fr['main'].unique())
    alter_ids = list(fr['friends_id'].unique())

    if debug:
        ego_ids = ego_ids[:5]
        alter_ids = alter_ids[:5]
        ego_fn = 'ego_ids_debug.txt'
        alter_fn = 'alter_ids_debug.txt'
    else:
        ego_fn = 'ego_ids.txt'
        alter_fn = 'alter_ids.txt'

    with open(ego_fn, 'w') as f:
        for item in ego_ids:
            f.write("%s\n" % item)
    with open(alter_fn, 'w') as f:
        for item in alter_ids:
            f.write("%s\n" % item)
    return ego_fn, alter_fn

def main(args):

    logging.info("2")
    # Create the text files and get the filenames
    logging.info(args.debug)

    ego_fn, alter_fn = make_txt_files(args.debug)
    logging.info("out")
    # Decide which file path to use based on a new argparse argument
    file_path = ego_fn if args.file_type == 'ego' else alter_fn

    logging.info(file_path)

    # Step 1: Create a compliance job
    upload_url, download_url, job_id = create_compliance_job(args.job_name, args.job_type)
    logging.info(f"Job created. Upload URL: {upload_url}, Download URL: {download_url}, Job ID: {job_id}")

    # Step 2: Upload your dataset
    upload_response = upload_dataset(upload_url, file_path)
    logging.info(f"Dataset uploaded. Response: {upload_response}")

    # Step 3: Check the status of your compliance job
    while True:
        status = get_compliance_job_status(job_id)
        logging.info(f"Job status: {status}")
        if status == 'complete':
            break
        elif status == 'failed':
            raise Exception("Compliance job failed.")
        time.sleep(60)  # wait for a minute before checking the status again

    # Step 4: Download the results
    results = download_results(download_url)
    logging.info("Downloaded results:")
    for entry in results:
        logging.info(entry)





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute a Twitter compliance job.")
    parser.add_argument("job_name", help="Name of the compliance job.")
    parser.add_argument("job_type", help="Type of the compliance job.", choices=["tweets", "users"])
    parser.add_argument("file_type", help="Type of file to use ('ego' or 'alter').", choices=["ego", "alter"])
    parser.add_argument("--debug", help="Run in debug mode. If set, use a different file path.", action="store_true")

    args = parser.parse_args()

    # Example usage
    # python batch_compliance_script.py ego_debug users ego --debug
    main(args)