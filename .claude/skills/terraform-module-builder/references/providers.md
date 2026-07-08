# Provider Version Constraints Reference

## AWS
```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
provider "aws" {
  region = var.region
}
```

## GCP
```hcl
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
```

## Azure
```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}
provider "azurerm" {
  features {}
}
```

## Kubernetes
```hcl
terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}
```

## Helm
```hcl
terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}
```

## Common Backend Configurations

### S3 (AWS)
```hcl
terraform {
  backend "s3" {
    # Configured via backend.tfvars
  }
}
```
`backend.tfvars`:
```hcl
bucket         = "my-project-terraform-state"
key            = "module-name/env/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "my-project-terraform-locks"
encrypt        = true
```

### GCS (GCP)
```hcl
terraform {
  backend "gcs" {}
}
```
`backend.tfvars`:
```hcl
bucket = "my-project-terraform-state"
prefix = "module-name/env"
```

### Azure Blob
```hcl
terraform {
  backend "azurerm" {}
}
```
`backend.tfvars`:
```hcl
resource_group_name  = "my-rg"
storage_account_name = "mystorageaccount"
container_name       = "tfstate"
key                  = "module-name/env/terraform.tfstate"
```