resource "aws_iam_role" "nib_db_access" {
  name               = "NIBDBAccess-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json

  tags = {
    Name        = "NIBDBAccess-${var.env}"
    Project     = "nib"
    Environment = var.env
  }
}

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "nib_db_access_policy" {
  name   = "nib-db-access-policy"
  role   = aws_iam_role.nib_db_access.id
  policy = data.aws_iam_policy_document.ssm_s3_access.json
}

resource "aws_iam_role_policy_attachment" "ssm_core_managed" {
  role       = aws_iam_role.nib_db_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "ssm_s3_access" {
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParameterHistory"
    ]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/nib/*"
    ]
  }

  statement {
    actions = [
      "s3:GetObject",
      "s3:HeadObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::nib-lambda-artifacts",
      "arn:aws:s3:::nib-lambda-artifacts/*"
    ]
  }
}

resource "aws_iam_instance_profile" "nib_db_access_profile" {
  name = "NIBDBAccessProfile-${var.env}"
  role = aws_iam_role.nib_db_access.name
}
