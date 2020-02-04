
resource "aws_subnet" "downloader" {
  cidr_block = cidrsubnet(aws_vpc.downloader.cidr_block, 3, 1)
  vpc_id = aws_vpc.downloader.id
  availability_zone = "us-east-1a"
}

resource "aws_route_table" "downloader" {
  vpc_id = aws_vpc.downloader.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.downloader.id
  }

  tags = {
    Name = "${terraform.workspace}-downloader"
  }
}

resource "aws_route_table_association" "downloader-subnet-association" {
  subnet_id = aws_subnet.downloader.id
  route_table_id = aws_route_table.downloader.id
}
