

# Output Account ID of AWS
data "aws_caller_identity" "current" {}
output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

# Output Region set for AWS
output "aws_region" {
    description = "Region set for AWS"
    value = var.aws_region
}

output "s3_bucket_name" {
    description = "Region set for AWS"
    value = var.s3_bucket
}
