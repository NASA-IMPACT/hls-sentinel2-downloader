resource "aws_vpc" "downloader" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = {
    Name = "${var.project_prefix}-downloader"
  }
}

resource "aws_security_group" "downloader" {
  vpc_id = aws_vpc.downloader.id

  // Allow all inbound.
  ingress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  // Allow all outbound.
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_eip" "downloader" {
  vpc = true
  instance = aws_instance.downloader.id
}

resource "aws_internet_gateway" "downloader" {
  vpc_id = aws_vpc.downloader.id
}
