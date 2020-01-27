data "template_file" "downloader" {
  template = file("task-definitions/downloader.json")

  vars = {
    image = aws_ecr_repository.downloader.repository_url
    log_group = aws_cloudwatch_log_group.downloader.name
    copernicus_username = var.copernicus_username
    copernicus_password = var.copernicus_password
  }
}

resource "aws_ecs_task_definition" "downloader" {
  family = "${terraform.workspace}-downloader"
  container_definitions = data.template_file.downloader.rendered
  requires_compatibilities = ["FARGATE"]
  network_mode = "awsvpc"
  cpu = "2048"
  memory = "16GB"
  execution_role_arn = aws_iam_role.execution_role.arn
  task_role_arn = aws_iam_role.task_role.arn
}
