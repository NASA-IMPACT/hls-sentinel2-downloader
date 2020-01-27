provider "aws" {
  region  = "us-east-1"
  profile = "default"
}

# It might be suitable to share states using S3 backend.
# terraform {
#   backend "s3" {
#     bucket = "tf-state-bucket-dev-hls"
#     key    = "terraform"
#     region = "us-east-1"
#     profile = "default"
#   }
# }
