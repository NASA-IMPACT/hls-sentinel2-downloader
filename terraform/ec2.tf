data "aws_ami" "ubuntu" {
  most_recent = true
  owners = ["099720109477"]

  filter {
    name = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*"]
  }

  filter {
      name = "virtualization-type"
      values = ["hvm"]
  }

  filter {
      name = "ena-support"
      values = ["true"]
  }
}

data "template_file" "startup_script" {
  template = file("../startup.sh")

  vars = {
    COPERNICUS_USERNAME = var.copernicus_username
    COPERNICUS_PASSWORD = var.copernicus_password
    UPLOAD_BUCKET = aws_s3_bucket.upload_bucket.id
    DOCKER_IMAGE = aws_ecr_repository.downloader.repository_url
    DB_URL = "postgresql://${var.database_user}:${var.database_password}@${aws_db_instance.downloader.address}/${var.database_name}"
  }
}

resource "aws_key_pair" "deployer" {
  key_name = "${var.project_prefix}-deployer-key"
  public_key = var.public_key
}

resource "aws_instance" "downloader" {
  ami = data.aws_ami.ubuntu.id
  instance_type = "m5d.xlarge"
  key_name = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.downloader.id]
  subnet_id = element(aws_subnet.downloader, 0).id
  iam_instance_profile = aws_iam_instance_profile.downloader_profile.name
  user_data = data.template_file.startup_script.rendered

  tags = {
    Name = "${var.project_prefix}-downloader"
  }
}
