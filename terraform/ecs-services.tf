#
# resource "aws_ecs_service" "downloader" {
#   name = "${terraform.workspace}-downloader"
#   cluster = aws_ecs_cluster.downloader.id
#   task_definition = aws_ecs_task_definition.downloader.arn
#   desired_count = 0
#   launch_type = "FARGATE"
#
#   deployment_minimum_healthy_percent = 100
#   deployment_maximum_percent = 200
#
#   network_configuration {
#     subnets = aws_subnet.private_subnets.*.id
#     security_groups = [aws_security_group.main.id]
#     assign_public_ip = true
#   }
# }
