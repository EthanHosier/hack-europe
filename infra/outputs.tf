output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_1_id" {
  description = "ID of the public subnet 1"
  value       = aws_subnet.public_1.id
}

output "public_subnet_2_id" {
  description = "ID of the public subnet 2"
  value       = aws_subnet.public_2.id
}

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.main.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.main.arn
}

output "security_group_alb_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "security_group_fargate_id" {
  description = "ID of the Fargate security group"
  value       = aws_security_group.fargate.id
}

output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_url" {
  description = "HTTPS URL of the CloudFront distribution"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "frontend_url" {
  description = "HTTPS URL where the frontend (S3) is served (same origin as CloudFront; /api* goes to backend)"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "frontend_bucket_name" {
  description = "S3 bucket for frontend static files (upload ui/dist here)"
  value       = aws_s3_bucket.frontend.id
}

output "api_domain" {
  description = "Custom domain for API / voice WebSocket (HTTPS/WSS)"
  value       = "api.${var.domain_name}"
}

output "voice_ws_url" {
  description = "WebSocket URL for Twilio voice stream (set in Twilio dashboard)"
  value       = "wss://api.${var.domain_name}/ws/voice/realtime"
}
