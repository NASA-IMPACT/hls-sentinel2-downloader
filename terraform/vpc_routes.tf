
resource "aws_subnet" "downloader" {
  count = length(data.aws_availability_zones.available.names)
  vpc_id = aws_vpc.downloader.id
  cidr_block = "10.0.${count.index + length(data.aws_availability_zones.available.names)}.0/24"
  availability_zone = element(data.aws_availability_zones.available.names, count.index)
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
  count = length(data.aws_availability_zones.available.names)
  subnet_id = aws_subnet.downloader[count.index].id
  route_table_id = aws_route_table.downloader.id
}
