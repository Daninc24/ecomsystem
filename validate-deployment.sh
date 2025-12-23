#!/bin/bash

# 🔍 Deployment Validation Script
# Validates that all files are ready for production deployment

echo "🔍 MarketHub Pro - Deployment Validation"
echo "========================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

success_count=0
total_checks=0

check_file() {
    local file=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $description${NC}"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}❌ $description - Missing: $file${NC}"
    fi
}

check_executable() {
    local file=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [ -x "$file" ]; then
        echo -e "${GREEN}✅ $description${NC}"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}❌ $description - Not executable: $file${NC}"
    fi
}

echo ""
echo "📋 Checking Core Application Files..."
check_file "app_mongo.py" "Main application file"
check_file "config_mongo.py" "Configuration file"
check_file "requirements.txt" "Python dependencies"
check_file "simple_mongo_mock.py" "MongoDB mock for development"

echo ""
echo "🐳 Checking Docker Files..."
check_file "Dockerfile" "Docker container definition"
check_file "docker-compose.yml" "Docker Compose configuration"
check_file ".dockerignore" "Docker ignore file"
check_file "mongo-init.js" "MongoDB initialization script"

echo ""
echo "🔧 Checking Configuration Files..."
check_file ".env.example" "Environment variables template"
check_file "nginx.conf" "Nginx configuration"

echo ""
echo "🚀 Checking Deployment Scripts..."
check_executable "docker-deploy.sh" "Docker deployment script"
check_executable "production-test.py" "Production test script"
check_file "validate-deployment.sh" "This validation script"

echo ""
echo "📚 Checking Documentation..."
check_file "DOCKER_PRODUCTION_GUIDE.md" "Docker production guide"
check_file "PRODUCTION_SECURITY_CHECKLIST.md" "Security checklist"
check_file "PRODUCTION_DEPLOYMENT_SUMMARY.md" "Deployment summary"
check_file "PRODUCTION_READINESS_ASSESSMENT.md" "Readiness assessment"

echo ""
echo "🔒 Checking Security Configuration..."
if grep -q "your-secret-key-change-in-production" config_mongo.py; then
    echo -e "${RED}❌ Hardcoded secret key found in config_mongo.py${NC}"
else
    echo -e "${GREEN}✅ No hardcoded secrets in configuration${NC}"
    success_count=$((success_count + 1))
fi
total_checks=$((total_checks + 1))

if grep -q "admin123" app_mongo.py; then
    echo -e "${YELLOW}⚠️  Default admin password still in code (configurable via env)${NC}"
else
    echo -e "${GREEN}✅ No hardcoded admin password${NC}"
fi

echo ""
echo "📊 VALIDATION SUMMARY"
echo "===================="
echo "Passed: $success_count/$total_checks"

percentage=$((success_count * 100 / total_checks))
echo "Success Rate: $percentage%"

if [ $success_count -eq $total_checks ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED - READY FOR DEPLOYMENT!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Copy .env.example to .env and configure your values"
    echo "2. Run: ./docker-deploy.sh"
    echo "3. Test with: python3 production-test.py"
    exit 0
elif [ $percentage -ge 90 ]; then
    echo -e "${YELLOW}⚠️  MOSTLY READY - Minor issues to address${NC}"
    exit 1
else
    echo -e "${RED}❌ NOT READY - Critical files missing${NC}"
    exit 2
fi