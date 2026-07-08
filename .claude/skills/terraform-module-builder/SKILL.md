---
name: terraform-module-builder
description: >
  This skill empowers Claude to build reusable Terraform modules based on user specifications.
  It generates production-ready, well-documented Terraform module code incorporating best practices
  for security, scalability, and multi-platform support. Use this skill when the user requests to
  create a new Terraform module, generate Terraform configuration, or needs help structuring
  infrastructure as code using Terraform. Always trigger this skill for phrases like "create Terraform
  module," "generate Terraform configuration," "Terraform module code," "infrastructure as code,"
  "write a Terraform module," "build a Terraform module," or any request involving Terraform
  resource definitions, providers, variables, or outputs. Even if the user just mentions wanting to
  "set up X with Terraform" or "IaC for X," trigger this skill immediately.
---

# Terraform Module Builder

## Overview

This skill generates a complete, production-ready Terraform module with the standard structure
including a `test/` folder that correctly invokes the module. Follow the steps below precisely.

---

## Required Output Structure

Every generated module **must** produce exactly this file tree:

```
<module-name>/
├── README.md
├── locals.tf
├── main.tf
├── outputs.tf
├── variables.tf
└── test/
    ├── Makefile
    ├── README.md
    ├── ecs.tf           ← replace with appropriate resource file(s) for the module
    ├── locals.tf
    ├── main.tf
    ├── outputs.tf
    ├── variables.tf
    └── vars/
        ├── backend.tfvars
        └── poc.tfvars
```

> The `test/ecs.tf` filename is an example. Name the file after the primary resource the test
> exercises (e.g., `s3.tf`, `rds.tf`, `vpc.tf`). You may add additional test resource files
> when useful.

---

## Step-by-Step Workflow

### 1. Gather Requirements

Before writing any code, ask the user for:

1. **Module name** – snake_case, e.g. `ecs_service`, `rds_cluster`
2. **Cloud provider** – AWS / GCP / Azure / other
3. **Primary resource(s)** – what Terraform resources will the module manage?
4. **Required variables** – inputs that callers must supply
5. **Optional variables** – inputs with sensible defaults
6. **Outputs** – values the module should export
7. **Environment context** – which environments (poc, dev, staging, prod)?
8. **Backend type** – S3/GCS/Azure Blob/local (for `backend.tfvars`)

If the user provides enough context upfront, infer reasonable defaults and proceed without asking.

---

### 2. Generate Module Root Files

#### `main.tf`
- Use the correct provider source and version constraints (`~> X.Y`)
- Include `terraform {}` block with `required_providers`
- Implement the primary resource(s) with all required arguments
- Reference `local.*` values for computed/derived config
- Follow naming convention: `resource "aws_ecs_service" "this" {}`

#### `variables.tf`
- Every variable must have: `description`, `type`, and `default` (or mark as required)
- Group variables logically with comments: `# --- Networking ---`, `# --- Compute ---`
- Use `sensitive = true` for secrets

#### `locals.tf`
- Define computed/derived values here to keep `main.tf` clean
- Common pattern: `name_prefix = "${var.project}-${var.environment}"`

#### `outputs.tf`
- Export all useful resource attributes (IDs, ARNs, endpoints, names)
- Always include `description` on each output

#### `README.md`
Use this template (fill in the blanks):

```markdown
# <Module Name> Terraform Module

## Overview
<One paragraph describing what this module provisions.>

## Usage
\`\`\`hcl
module "<module_name>" {
  source = "../"

  # required variables
  <variable> = "<value>"
}
\`\`\`

## Requirements
| Name | Version |
|------|---------|
| terraform | >= 1.3.0 |
| <provider> | ~> X.Y |

## Inputs
| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
<fill from variables.tf>

## Outputs
| Name | Description |
|------|-------------|
<fill from outputs.tf>
```

---

### 3. Generate `test/` Folder

The `test/` folder is a **standalone Terraform root module** that calls the parent module.
It must be fully self-contained and runnable with `terraform init && terraform apply`.

#### `test/main.tf`
```hcl
terraform {
  required_version = ">= 1.3.0"

  required_providers {
    <provider> = {
      source  = "<registry>/<provider>"
      version = "~> X.Y"
    }
  }

  backend "s3" {}   # or appropriate backend; parameterised via backend.tfvars
}

provider "<provider>" {
  region = var.region   # or appropriate top-level config
}
```

#### `test/ecs.tf` (or appropriately named resource file)
```hcl
module "<module_name>" {
  source = "../"

  # Pass through all required variables using locals or vars
  <variable> = local.<variable>
  # ...
}
```

> **Rule:** every required variable of the parent module **must** be supplied in this call.

#### `test/variables.tf`
- Mirror the parent module's required variables so they can be injected via `poc.tfvars`
- Add any test-specific variables (e.g., `region`, `account_id`)

#### `test/locals.tf`
```hcl
locals {
  name_prefix = "${var.project}-${var.environment}"
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

#### `test/outputs.tf`
- Re-export the module's outputs for visibility during test runs

#### `test/vars/backend.tfvars`
```hcl
bucket         = "<project>-terraform-state"
key            = "<module-name>/poc/terraform.tfstate"
region         = "us-east-1"      # adjust per provider
dynamodb_table = "<project>-terraform-locks"
encrypt        = true
```

#### `test/vars/poc.tfvars`
```hcl
# Environment
project     = "<project-name>"
environment = "poc"
region      = "us-east-1"

# Module-specific required variables
<variable> = "<example-value>"
```

#### `test/Makefile`
```makefile
VARS_FILE  ?= vars/poc.tfvars
BACKEND    ?= vars/backend.tfvars
TF         := terraform

.PHONY: init plan apply destroy fmt validate

init:
	$(TF) init -backend-config=$(BACKEND) -reconfigure

validate: init
	$(TF) validate

fmt:
	$(TF) fmt -recursive

plan: init
	$(TF) plan -var-file=$(VARS_FILE)

apply: init
	$(TF) apply -var-file=$(VARS_FILE) -auto-approve

destroy: init
	$(TF) destroy -var-file=$(VARS_FILE) -auto-approve
```

#### `test/README.md`
```markdown
# Test – <Module Name>

End-to-end test that provisions the `<module-name>` module in a real cloud account.

## Prerequisites
- Terraform >= 1.3.0
- Credentials for <provider> configured (env vars or profile)
- A state backend bucket/container already created

## Usage

\`\`\`bash
# 1. Initialise with remote backend
make init

# 2. Review the plan
make plan

# 3. Apply
make apply

# 4. Clean up
make destroy
\`\`\`

## Variables
Edit `vars/poc.tfvars` to match your environment before running.
```

---

### 4. Best Practices Checklist

Apply the following to every generated module:

- [ ] **Tagging** – include a `tags` variable (type `map(string)`) with `default = {}`; merge with module-managed tags in `locals.tf`
- [ ] **Least privilege** – IAM policies should grant only the permissions needed
- [ ] **Encryption** – enable encryption at rest and in transit where applicable
- [ ] **Versioning / lifecycle** – add `lifecycle` blocks to protect stateful resources
- [ ] **No hardcoded regions or account IDs** – use `data "aws_region"` / `data "aws_caller_identity"` or variables
- [ ] **Provider version constraints** – always use `~>` pessimistic constraint
- [ ] **Terraform version constraint** – `required_version = ">= 1.3.0"` (or appropriate)
- [ ] **Consistent naming** – all resources use `local.name_prefix` or similar derived name

---

### 5. Delivery

1. Write every file to the filesystem under `<module-name>/` directory.
2. Use `present_files` to share all generated files with the user.
3. Print a brief summary: what the module provisions, key variables, and how to run the test.

---

## Reference Files

- `references/providers.md` — common provider version constraints and registry sources
- `references/patterns.md` — reusable HCL patterns (IAM, tagging, lifecycle, encryption)
- `assets/templates/` — skeleton `.tf` files for quick scaffolding