resource "aws_iam_role" "downloader_role" {
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_instance_profile" "downloader_profile" {
  role = aws_iam_role.downloader_role.name
}


resource "aws_iam_policy" "downloader_role" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "*",
      "Resource": "*",
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "downloader_role" {
  role = aws_iam_role.downloader_role.name
  policy_arn = aws_iam_policy.downloader_role.arn
}
