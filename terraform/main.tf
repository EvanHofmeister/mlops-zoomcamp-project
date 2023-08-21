terraform {
    required_version = ">= 1.5.5"

    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "~> 4.67.0"
        }
    }
}

# Configure AWS provider
provider "aws" {
    region = var.aws_region
}

# Create S3 bucket
resource "aws_s3_bucket" "mlops_bucket" {
  bucket = var.s3_bucket
  force_destroy = true # will delete contents of bucket when we run terraform destroy
}

# Set access control of bucket to private
resource "aws_s3_bucket_acl" "s3_reddit_bucket_acl" {
  bucket = aws_s3_bucket.mlops_bucket.id
  acl    = "private"
  depends_on = [aws_s3_bucket_ownership_controls.s3_bucket_acl_ownership]
}

# Resource to avoid error "AccessControlListNotSupported: The bucket does not allow ACLs"
resource "aws_s3_bucket_ownership_controls" "s3_bucket_acl_ownership" {
  bucket = aws_s3_bucket.mlops_bucket.id
  rule {
    object_ownership = "ObjectWriter"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

variable "ingressrules" {
  type    = list(number)
  default = [22, 8888]
}

resource "aws_security_group" "web_traffic" {
  name        = "Allow web traffic"
  description = "Allow ssh and strandard http/https inbound and everthing outbound"

  dynamic "ingress" {
    iterator = port
    for_each = var.ingressrules
    content {
      from_port   = port.value
      to_port     = port.value
      protocol    = "tcp"
      cidr_blocks = var.ingress_cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

#Resource to Create Key Pair
resource "aws_key_pair" "demo_key_pair" {
  key_name   = var.key_pair_name
  public_key = var.public_key
}

#Example Instance Creation using Key Pair
resource "aws_instance" "demo-instance" {
  ami = "ami-05d251e0fc338590c"
  instance_type = "t2.micro"
  security_groups = [aws_security_group.web_traffic.name]
  key_name      = aws_key_pair.demo_key_pair.key_name
}