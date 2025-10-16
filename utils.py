from typing import List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv
from urllib.parse import quote
import os, requests, boto3, urllib.parse, unicodedata, re
from boto3.s3.transfer import TransferConfig

# Set up Jinja environment
env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(['html', 'xml'])
)

# Funtion to generate html based on template
def gerar_html_from_data(dados: dict) -> str:
    """Render HTML from a template and data dict."""
    match dados.get('template'):
        case 'advogado':
            template = env.get_template("template_adv_nova.html")
        case 'reclamante':
            template = env.get_template("template_rec_nova.html")
        case _:
            template = env.get_template("template_rec_nova.html")
    rendered_html = template.render(**dados)
    return rendered_html

# Helper to ensure content for metadata
def ascii_for_s3_meta(value: str) -> str:
    norm = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in norm if ord(ch) < 128)

# Helper to ensure content before sending to S3
def content_disposition(filename: str, inline: bool = True) -> str:
    disp = "inline" if inline else "attachment"
    ascii_name = ascii_for_s3_meta(filename) or "file"
    return f"{disp}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"

# Helper to ensure direct filename
def safe_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1].strip()
    return name or "arquivo.pdf"

def find_next_versioned_filename_list(s3_client: boto3.client, bucket: str, folder: str, original_filename: str) -> str:
    base_name, ext = os.path.splitext(original_filename)
    
    s3_prefix = f"{folder}{base_name}"
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=s3_prefix, MaxKeys=1000)
    
    existing_keys: List[str] = []
    
    version_pattern = re.compile(rf"^{re.escape(base_name)}(?:_v(\d+))?{re.escape(ext)}$")

    for page in pages:
        if 'Contents' in page:
            for item in page['Contents']:
                key = item['Key']
                
                filename_only = key[len(folder):]
                if version_pattern.match(filename_only):
                    existing_keys.append(filename_only)

    if not existing_keys:
        return original_filename
    
    max_version = 0
    
    for key in existing_keys:
        match = version_pattern.match(key)
        if match:
            if key == original_filename:
                max_version = max(max_version, 1)
            
            version_num = match.group(1)
            if version_num:
                max_version = max(max_version, int(version_num))

    next_version = max_version + 1
    
    if next_version == 1:
        return original_filename
    else:
        return f"{base_name}_v{next_version}{ext}"

# Function to access AWS S3
def get_access_s3():
    # Get necessary keys
    load_dotenv()
    reg = os.getenv('AWS_S3_REG')
    pub = os.getenv('AWS_S3_PUBLIC')
    priv = os.getenv('AWS_S3_PRIVATE')
    bucket = os.getenv('AWS_S3_BUCKET')

    if not all([reg, pub, priv, bucket]):
        raise ValueError("One or more environment variables are missing.")

    s3_client = boto3.client(
        service_name = 's3', region_name = reg,
        aws_access_key_id = pub, aws_secret_access_key = priv
    )

    return s3_client, bucket, reg

# Function to send file to AWS S3
def send_file_s3(file, filename):
    # Get S3 access
    s3_client, bucket, reg = get_access_s3()
    S3_TRANSFER_CONFIG = TransferConfig(multipart_threshold=8*1024*1024,
                                    multipart_chunksize=8*1024*1024,
                                    max_concurrency=4,
                                    use_threads=True)

    # Store file and retrieve link access
    try:
        file.seek(0)
        original_safe_name = safe_filename(filename)
        folder = 'propostas/'

        final_filename = find_next_versioned_filename_list(
            s3_client, bucket, folder, original_safe_name
        )

        extra_args = {
            "ContentType": "application/pdf",
            "ContentDisposition": content_disposition(final_filename, inline=True),
            "Metadata": {"filename": ascii_for_s3_meta(final_filename)},
        }
        if getattr(file, "mimetype", None):
            extra_args["ContentType"] = file.mimetype

        s3_key = f"{folder}{final_filename}"
        s3_client.upload_fileobj(
            file, bucket, s3_key, ExtraArgs=extra_args, Config=S3_TRANSFER_CONFIG
        )

        url_name = urllib.parse.quote_plus(final_filename)
        link = f"https://{bucket}.s3.{reg}.amazonaws.com/{folder}{url_name}"

        return link
    except Exception as e:
        raise Exception(e)

# Function for the scheduler timer
def keep_alive():
    try:
        load_dotenv()
        SELF = os.getenv('SELF_URL')
        response = requests.get(f'{SELF}/ping')
        print("Keep-alive request sent successfully") if response.status_code == 200 else print("Alive failed")
    except Exception as e:
        print(f"Error during Keep-Alive request: {e}")