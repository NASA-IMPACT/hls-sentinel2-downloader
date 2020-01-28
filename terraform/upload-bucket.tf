resource "aws_s3_bucket" "upload_bucket" {
  bucket = "${terraform.workspace}-uploads"
}
