import boto3

class Client(object):
    def __init__(self, key, secret, region="us-east-1"):
        self.client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=key,
            aws_secret_access_key=secret)

    def list_objects(self, bucket, root):
        """
        checks a given s3 location for new emails
        """
        prefix = root.strip("/") + "/"
        objects = []
        params = {
            "Bucket": bucket,
            #"Prefix": prefix,
            "Delimiter": "/",
            "MaxKeys": 1000
        }
        while True:
            resp = self.client.list_objects_v2(**params)
            # common_prefixes += resp.get("CommonPrefixes", [])
            for obj in resp.get("Contents", []):
                if obj["Size"] > 0:
                    objects.append(obj)
            if "NextContinuationToken" in resp:
                params["ContinuationToken"] = resp["NextContinuationToken"]
            else:
                break
        return objects

    def get_object(self, bucket, key, file_handle):
        self.client.download_fileobj(bucket, key, file_handle)

    def put_object(self, data, bucket, key):
        self.client.put_object(Body=data, Bucket=bucket, Key=key)

    def copy_object(self, src_bucket, src_key, tgt_bucket, tgt_key):
        src = {"Bucket": src_bucket, "Key": src_key}
        self.client.copy_object(CopySource=src, Bucket=tgt_bucket, Key=tgt_key)

    def delete_object(self, bucket, key):
        self.client.delete_object(Bucket=bucket, Key=key)