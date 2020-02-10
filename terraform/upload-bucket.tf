resource "aws_s3_bucket" "upload_bucket" {
  bucket_prefix = "${terraform.workspace}-uploads"
}
