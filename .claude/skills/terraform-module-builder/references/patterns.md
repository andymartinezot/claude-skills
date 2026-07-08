# Reusable HCL Patterns

## Tagging Pattern (AWS)
```hcl
# variables.tf
variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# locals.tf
locals {
  default_tags = {
    Module      = "<module-name>"
    ManagedBy   = "terraform"
    Project     = var.project
    Environment = var.environment
  }
  tags = merge(local.default_tags, var.tags)
}

# usage in resource
resource "aws_s3_bucket" "this" {
  bucket = local.name_prefix
  tags   = local.tags
}
```

## Naming Pattern
```hcl
# locals.tf
locals {
  name_prefix = "${var.project}-${var.environment}"
  # Usage: "${local.name_prefix}-<resource-suffix>"
}
```

## IAM Least Privilege Pattern (AWS)
```hcl
data "aws_iam_policy_document" "this" {
  statement {
    sid    = "AllowSpecificActions"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.this.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "this" {
  name   = "${local.name_prefix}-policy"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.this.json
}
```

## Lifecycle Protection Pattern
```hcl
resource "aws_db_instance" "this" {
  # ...
  lifecycle {
    prevent_destroy       = true
    ignore_changes        = [password]
    create_before_destroy = false
  }
}
```

## Encryption Pattern (AWS S3)
```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}
```

## Data Sources for Dynamic Values (AWS)
```hcl
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  partition  = data.aws_partition.current.partition
}
```

## Conditional Resource Creation
```hcl
variable "create_bucket" {
  description = "Whether to create the S3 bucket"
  type        = bool
  default     = true
}

resource "aws_s3_bucket" "this" {
  count  = var.create_bucket ? 1 : 0
  bucket = local.name_prefix
}

# Reference with:
output "bucket_id" {
  value = try(aws_s3_bucket.this[0].id, null)
}
```

## For_each Pattern (map of resources)
```hcl
variable "buckets" {
  description = "Map of bucket configurations"
  type = map(object({
    versioning = bool
    lifecycle  = bool
  }))
  default = {}
}

resource "aws_s3_bucket" "this" {
  for_each = var.buckets
  bucket   = "${local.name_prefix}-${each.key}"
}
```

## Sensitive Variable Pattern
```hcl
variable "db_password" {
  description = "Master password for the RDS instance"
  type        = string
  sensitive   = true
}
```

## ECS Service Pattern (AWS)
```hcl
resource "aws_ecs_service" "this" {
  name            = "${local.name_prefix}-service"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}
```