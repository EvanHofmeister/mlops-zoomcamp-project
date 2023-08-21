variable "db_password" {
  description = "Password for Redshift master DB user"
  type        = string
  default     = "<Password>"
}

variable "s3_bucket" {
  description = "Bucket name for S3"
  type        = string
  default     = "mlops-s3-v2"
}

variable "aws_region" {
  description = "Region for AWS"
  type        = string
  default     = "us-east-2"
}

variable "key_pair_name" {
  description = "Name of EC2 key pair name"
  type        = string
  default     = "mlops-key-pair2"
}

variable "public_key" {
  description = "EC2 key pair public key"
  type        = string
  default     = "<Public key created with SSH Keygen>"
}

variable "ingress_cidr_blocks" {
  # Search on Google "what is my ip".
  description = "List of IPv4 CIDR ranges to use on all ingress rules"
  type        = list(string)
  default     = ["Your IP Address/32"]
}