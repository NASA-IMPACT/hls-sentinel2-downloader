
resource "aws_lambda_function" "reviewer" {
  function_name = "${terraform.workspace}-reviewer"
  handler = "main.handler"
  runtime = "python3.8"
  timeout = 900
  memory_size = 1600

  role = "${aws_iam_role.iam_for_lambda.arn}"
  s3_bucket = "${aws_s3_bucket.lambda_bucket.id}"
  s3_key = "reviewer.zip"
  source_code_hash = "${filebase64sha256("../build/reviewer.zip")}"

  vpc_config {
    subnet_ids = [aws_subnet.downloader.id]
    security_group_ids = [aws_security_group.downloader.id]
  }

  environment {
    variables = {
      DB_URL = "postgresql://${var.database_user}:${var.database_password}@${aws_db_instance.downloader.address}/${var.database_name}"
        COPERNICUS_USERNAME = var.copernicus_username
        COPERNICUS_PASSWORD = var.copernicus_password
        UPLOAD_BUCKET = aws_s3_bucket.upload_bucket.id
    }
  }

  depends_on = [
    "aws_iam_role_policy_attachment.lambda_role",
  ]
}


resource "aws_cloudwatch_event_rule" "reviewer_schedule" {
  name                = "${terraform.workspace}-reviewer-schedule"
  description         = "Fires sentinel-2 granules reviewer periodically"
  schedule_expression = "rate(5 hours)"
}

resource "aws_cloudwatch_event_target" "reviewer_schedule_target" {
  rule      = "${aws_cloudwatch_event_rule.reviewer_schedule.name}"
  target_id = "lambda"
  arn       = "${aws_lambda_function.reviewer.arn}"
}


resource "aws_lambda_permission" "allow_cloudwatch_to_call_reviewer" {
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.reviewer.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.reviewer_schedule.arn}"
}
