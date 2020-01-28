resource "aws_ecs_cluster" "downloader" {
  name = "${terraform.workspace}-downloader"
}

resource "aws_cloudwatch_log_group" "downloader" {
  name = "${terraform.workspace}-downloader"
}
