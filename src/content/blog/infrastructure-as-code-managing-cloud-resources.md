---
title: "Infrastructure as code: managing cloud resources from version control."
description: "What infrastructure as code is, why it matters, and how Terraform and Pulumi approach the problem differently."
pubDate: 2026-02-02
tags: ["Architecture"]
draft: false
---

Before infrastructure as code, provisioning a server meant logging into a cloud console, clicking through a wizard, and hoping you remembered what you did when you needed to do it again. Infrastructure as code (IaC) replaces that with files that describe what infrastructure should exist, which you commit to version control like any other code.

## Why it matters

**Reproducibility.** A Terraform file that describes your VPC, subnets, security groups, and EC2 instances will produce identical infrastructure every time you apply it. No more "it works in staging but prod has a slightly different security group."

**Change tracking.** Every infrastructure change goes through a pull request. You can see who changed what, when, and why. Rolling back means reverting a commit.

**Disaster recovery.** If you lose a region or need to spin up a new environment, your infrastructure definitions are your blueprint. With IaC, rebuilding from scratch takes minutes, not days.

**Drift detection.** IaC tools can detect when the actual state of infrastructure diverges from what the code describes -- someone clicked something in the console -- and report or fix it.

## Terraform basics

Terraform is the most widely used IaC tool. You write `.tf` files in HCL (HashiCorp Configuration Language), run `terraform plan` to preview changes, and `terraform apply` to execute them.

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "assets" {
  bucket = "my-app-assets-prod"
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

```bash
terraform init    # download providers
terraform plan    # show what will change
terraform apply   # make it so
```

Terraform tracks state in a `terraform.tfstate` file. In production, store state remotely in S3 or Terraform Cloud so the team shares the same state and concurrent applies don't conflict:

```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}
```

## Variables and modules

Hard-coding values defeats the purpose. Use variables for environment-specific values:

```hcl
variable "environment" {
  type    = string
  default = "staging"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

resource "aws_instance" "app" {
  instance_type = var.instance_type
  tags = {
    Environment = var.environment
  }
}
```

Modules let you package reusable infrastructure definitions:

```hcl
module "web_server" {
  source        = "./modules/web-server"
  environment   = "prod"
  instance_type = "t3.small"
}
```

## Pulumi: IaC in real programming languages

Terraform's HCL is declarative but limited -- no real loops, conditionals, or abstractions beyond modules. Pulumi takes a different approach: write infrastructure in TypeScript, Python, Go, or C#.

```typescript
import * as aws from "@pulumi/aws";

const bucket = new aws.s3.Bucket("assets", {
  versioning: { enabled: true },
});

// Real TypeScript: loops, functions, conditionals
const environments = ["staging", "prod"];
const buckets = environments.map(env =>
  new aws.s3.Bucket(`assets-${env}`, {
    tags: { Environment: env },
  })
);

export const bucketNames = buckets.map(b => b.bucket);
```

Pulumi gives you the full expressive power of a programming language while still managing state and detecting drift. The tradeoff: more power means more ways to write infrastructure that's hard to read.

## The workflow

A mature IaC workflow looks like:

1. Developer makes changes to `.tf` files in a feature branch
2. `terraform plan` output is posted as a CI comment on the PR
3. Team reviews the plan -- what resources will be created, modified, or destroyed
4. Merge triggers `terraform apply` in CI/CD against the target environment

The critical thing is that no one applies infrastructure changes manually. The PR and plan are the review mechanism; the apply is automated.

The hardest part of adopting IaC is often not the tooling -- it's changing the habit of clicking in the console. Once your team has felt the pain of untracked infrastructure changes, the habit change becomes easy.
