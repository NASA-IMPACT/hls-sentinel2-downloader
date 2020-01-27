resource "aws_route_table" "public_routes" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}


resource "aws_subnet" "public_subnets" {
  count = length(data.aws_availability_zones.available.names)
  vpc_id = aws_vpc.main.id
  cidr_block = "10.0.${count.index + length(data.aws_availability_zones.available.names)}.0/24"
  availability_zone = element(data.aws_availability_zones.available.names, count.index)
}

resource "aws_route_table_association" "public_subnet_routes" {
  count = length(data.aws_availability_zones.available.names)
  subnet_id = aws_subnet.public_subnets[count.index].id
  route_table_id = aws_route_table.public_routes.id
}
