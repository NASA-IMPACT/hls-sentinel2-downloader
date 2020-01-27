resource "aws_route_table" "private_routes" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
}

resource "aws_subnet" "private_subnets" {
  count = length(data.aws_availability_zones.available.names)
  vpc_id = aws_vpc.main.id
  cidr_block = "10.0.${count.index}.0/24"
  availability_zone = element(data.aws_availability_zones.available.names, count.index)
}

resource "aws_route_table_association" "private_subnet_routes" {
  count = length(data.aws_availability_zones.available.names)
  subnet_id = aws_subnet.private_subnets[count.index].id
  route_table_id = aws_route_table.private_routes.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id = aws_vpc.main.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"
  route_table_ids = [aws_route_table.private_routes.id]
}
