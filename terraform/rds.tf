resource "aws_db_subnet_group" "rds" {
  subnet_ids = aws_subnet.downloader.*.id
}

resource "aws_security_group" "rds" {
  vpc_id = aws_vpc.downloader.id

  ingress {
    protocol = "tcp"
    from_port = 5432
    to_port = 5432
    security_groups = [aws_security_group.downloader.id]
  }

  // Allow all outbound.
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "downloader" {
  identifier = "${var.project_prefix}-database"
  engine = "postgres"
  allocated_storage = var.database_allocated_storage
  instance_class = var.database_instance_class
  name = var.database_name
  username = var.database_user
  password = var.database_password
  db_subnet_group_name = aws_db_subnet_group.rds.id
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot = true
}
