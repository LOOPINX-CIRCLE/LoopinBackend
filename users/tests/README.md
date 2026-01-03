# User Authentication Test Suite

Comprehensive test coverage for the Loopin Backend user authentication system.

## 📋 Test Files

### 1. `test_comprehensive_auth.py`
**Complete API and Model Tests**

- **PhoneOTPModelTests** (11 tests)
  - OTP creation, generation, verification
  - Expiration handling
  - Attempt tracking
  - Unique constraints

- **EventInterestModelTests** (3 tests)
  - Creation and uniqueness
  - Ordering

- **UserProfileModelTests** (4 tests)
  - Profile creation
  - Default values
  - Relationships with interests
  - Gender choices

- **SignupAPITests** (7 tests)
  - New user signup
  - Existing user scenarios
  - Phone format validation
  - Twilio integration
  - OTP record creation

- **OTPVerificationAPITests** (9 tests)
  - Successful verification
  - User and profile creation
  - Invalid/expired OTP handling
  - Max attempts
  - Format validation

- **CompleteProfileAPITests** (15 tests)
  - Profile completion success
  - Token validation
  - Name validation (length, characters)
  - Age validation (18+)
  - Gender validation
  - Event interests (count, active/inactive)
  - Profile pictures (count, URL format)
  - Bio length validation

- **LoginAPITests** (4 tests)
  - Existing user login
  - Non-existing user
  - Twilio failures
  - Phone format validation

- **VerifyLoginAPITests** (4 tests)
  - Successful login verification
  - Invalid/expired OTP
  - No OTP record

- **GetProfileAPITests** (3 tests)
  - Profile retrieval
  - Token validation
  - Missing token

- **GetEventInterestsAPITests** (3 tests)
  - Retrieval of interests
  - Empty state
  - Ordering

- **LogoutAPITests** (1 test)
  - Logout functionality

- **JWTTokenTests** (3 tests)
  - Token creation
  - Token verification
  - Expired/invalid tokens

- **EdgeCaseTests** (4 tests)
  - International phone formats
  - Concurrent OTP requests
  - Boundary values
  - Special characters in names

**Total: 71 tests**

### 2. `test_services.py`
**Twilio Service Tests**

- **TwilioServiceTests** (9 tests)
  - SMS sending success/failure
  - Test mode
  - Trial account restrictions
  - Phone normalization
  - Missing credentials
  - Verify service integration

- **TwilioServiceEdgeCasesTests** (7 tests)
  - Special characters in phone
  - Message format verification
  - Network timeouts
  - Case-insensitive test mode
  - Empty phone numbers
  - Rate limiting

**Total: 16 tests**

### 3. `test_schemas.py`
**Pydantic Schema Validation Tests**

- **TestPhoneNumberRequest** (7 tests)
  - Valid formats
  - Normalization
  - Too short/long
  - Invalid characters

- **TestOTPVerificationRequest** (4 tests)
  - Valid OTP
  - Length validation
  - Digit-only validation
  - No spaces

- **TestCompleteProfileRequest** (14 tests)
  - Valid profile data
  - Name validation (length, characters, whitespace)
  - Birth date (age 18+, format)
  - Gender validation
  - Event interests (count 1-5)
  - Profile pictures (count 1-6, URL format)
  - Bio max length
  - Optional fields

- **TestLoginRequest** (2 tests)
  - Valid login
  - OTP validation

- **TestAuthResponse** (2 tests)
  - Success/failure responses

- **TestEventInterestResponse** (1 test)
  - Response structure

- **TestUserProfileResponse** (1 test)
  - Response structure

**Total: 31 tests**

## 📊 Coverage Summary

| Component | Tests | Coverage Areas |
|-----------|-------|----------------|
| Models | 18 | OTP, Profile, EventInterest |
| API Endpoints | 46 | Signup, Login, Profile, Verification |
| Services | 16 | Twilio SMS, OTP sending |
| Schemas | 31 | Pydantic validation |
| JWT | 3 | Token creation/verification |
| Edge Cases | 4 | Boundary conditions |

**Grand Total: 118 comprehensive tests**

## 🚀 Running Tests

### Run All Tests
```bash
# Inside Docker
docker-compose exec web python manage.py test users.tests

# Or with pytest
docker-compose exec web pytest users/tests/
```

### Run Specific Test File
```bash
docker-compose exec web python manage.py test users.tests.test_comprehensive_auth
docker-compose exec web python manage.py test users.tests.test_services
docker-compose exec web python manage.py test users.tests.test_schemas
```

### Run Specific Test Class
```bash
docker-compose exec web python manage.py test users.tests.test_comprehensive_auth.SignupAPITests
```

### Run with Coverage
```bash
docker-compose exec web coverage run --source='users' manage.py test users.tests
docker-compose exec web coverage report
docker-compose exec web coverage html  # Generate HTML report
```

### Run with Verbose Output
```bash
docker-compose exec web python manage.py test users.tests -v 2
```

## 🧪 Test Categories

### 1. **Unit Tests**
- Model methods (OTP generation, verification)
- Schema validation
- JWT token utilities

### 2. **Integration Tests**
- API endpoints with database
- Twilio service integration
- Authentication flow

### 3. **Edge Case Tests**
- Boundary values
- Special characters
- Concurrent operations
- Network failures

## ✅ Test Coverage Areas

### Authentication Flow
- [x] Phone number signup
- [x] OTP generation and sending
- [x] OTP verification
- [x] User creation
- [x] Profile completion
- [x] Login
- [x] Token generation
- [x] Profile retrieval

### Validation
- [x] Phone number formats
- [x] OTP format (4 digits)
- [x] Name validation
- [x] Age verification (18+)
- [x] Gender validation
- [x] Event interests (1-5)
- [x] Profile pictures (1-6 URLs)
- [x] Bio length (max 500)

### Security
- [x] JWT token expiration
- [x] Invalid token handling
- [x] OTP expiration
- [x] Max OTP attempts
- [x] Token verification

### Edge Cases
- [x] International phone formats
- [x] Concurrent OTP requests
- [x] Network timeouts
- [x] Rate limiting
- [x] Special characters
- [x] Boundary values

## 🐛 Testing Best Practices

1. **Isolation**: Each test is independent
2. **Mocking**: External services (Twilio) are mocked
3. **Coverage**: Every code path is tested
4. **Edge Cases**: Boundary conditions are validated
5. **Documentation**: Tests are well-documented
6. **Assertions**: Clear, specific assertions

## 📝 Adding New Tests

When adding new functionality:

1. Write tests first (TDD approach)
2. Cover happy path
3. Test error cases
4. Validate edge cases
5. Check boundary conditions
6. Update this README

## 🔍 Debugging Failed Tests

```bash
# Run with detailed output
docker-compose exec web python manage.py test users.tests -v 3

# Run specific failing test
docker-compose exec web python manage.py test users.tests.test_comprehensive_auth.SignupAPITests.test_signup_new_user_success

# Use pdb for debugging
# Add: import pdb; pdb.set_trace() in test
docker-compose exec web python manage.py test users.tests --pdb
```

## 📈 Continuous Integration

Tests should run automatically on:
- Every commit
- Pull request creation
- Before deployment
- Scheduled (nightly)

## 🎯 Quality Metrics

- **Code Coverage**: Target 90%+
- **Test Success Rate**: 100%
- **Test Execution Time**: < 30 seconds
- **Maintainability**: All tests documented

---

**Last Updated**: October 2025  
**Maintained By**: Loopin Backend Team

