import boto3
import configargparse
p = configargparse.ArgParser()
p.add('--s3_uri', default='s3://export-test-tmuth/test1', help='The full path of the bucket to delete, ie s3://export-test-tmuth/test1/test1.txt')
global options
options = p.parse_args()

def split_s3_path(s3_path):
    path_parts=s3_path.replace("s3://","").split("/")
    bucket=path_parts.pop(0)
    key="/".join(path_parts)
    return bucket, key

bucket, tmp_key = split_s3_path(options.s3_uri)


s3 = boto3.resource('s3')
bucket = s3.Bucket(bucket)
bucket.objects.filter(Prefix=tmp_key).delete()
