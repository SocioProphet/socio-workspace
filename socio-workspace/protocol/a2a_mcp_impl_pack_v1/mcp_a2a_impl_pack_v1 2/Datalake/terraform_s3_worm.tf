resource "aws_s3_bucket" "worm" {
  bucket = "sourceos-worm-bucket"
  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.worm.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_object_lock_configuration" "lock" {
  bucket = aws_s3_bucket.worm.id
  rule { default_retention { mode = "COMPLIANCE" days = 365 } }
}
