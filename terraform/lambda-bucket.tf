resource "aws_s3_bucket" "lambda_bucket" {
  bucket = "${terraform.workspace}-lambda"
}
