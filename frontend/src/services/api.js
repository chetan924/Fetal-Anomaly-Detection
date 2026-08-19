import axios from 'axios';


// ============================================================
// API CONFIGURATION
// ============================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8001';


const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});


// ============================================================
// REQUEST INTERCEPTOR
// ============================================================

api.interceptors.request.use(
  (config) => {
    const token =
      localStorage.getItem('access_token');

    /*
     * Add JWT only when available.
     */

    if (token) {
      config.headers =
        config.headers || {};

      config.headers.Authorization =
        `Bearer ${token}`;
    }

    return config;
  },

  (error) => {
    return Promise.reject(error);
  }
);


// ============================================================
// RESPONSE INTERCEPTOR
// ============================================================

api.interceptors.response.use(
  (response) => {
    return response;
  },

  (error) => {
    /*
     * Handle unauthorized requests.
     */

    if (
      error.response?.status === 401
    ) {
      console.warn(
        'Authentication failed: 401 Unauthorized'
      );

      const requestUrl =
        error.config?.url || '';

      /*
       * Don't remove JWT for authentication
       * requests because login/register/forgot
       * password don't require an existing JWT.
       */

      const isAuthRequest =
        requestUrl.includes(
          '/api/auth/login'
        ) ||
        requestUrl.includes(
          '/api/auth/register'
        ) ||
        requestUrl.includes(
          '/api/auth/forgot-password'
        ) ||
        requestUrl.includes(
          '/api/auth/reset-password'
        );

      if (!isAuthRequest) {
        localStorage.removeItem(
          'access_token'
        );
      }
    }

    return Promise.reject(error);
  }
);


// ============================================================
// ERROR MESSAGE HELPER
// ============================================================

export const getApiErrorMessage = (
  error,
  fallback = 'Something went wrong. Please try again.'
) => {
  const detail =
    error?.response?.data?.detail;


  /*
   * FastAPI validation error:
   *
   * detail: [
   *   {
   *     type: "...",
   *     loc: [...],
   *     msg: "..."
   *   }
   * ]
   */

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (
          typeof item === 'string'
        ) {
          return item;
        }

        return (
          item?.msg ||
          'Invalid request.'
        );
      })
      .join(', ');
  }


  /*
   * Normal FastAPI detail string.
   */

  if (
    typeof detail === 'string'
  ) {
    return detail;
  }


  /*
   * Custom API message.
   */

  if (
    typeof error?.response?.data?.message ===
    'string'
  ) {
    return error.response.data.message;
  }


  /*
   * Axios error message.
   */

  if (
    typeof error?.message ===
    'string'
  ) {
    return error.message;
  }


  return fallback;
};


// ============================================================
// HEALTH
// ============================================================

export const healthCheck = async () => {
  const response =
    await api.get('/health');

  return response.data;
};


// ============================================================
// AUTH
// ============================================================


// ============================================================
// REGISTER
// ============================================================
//
// POST /api/auth/register
//
// Request:
//
// {
//   full_name,
//   email,
//   password
// }
//
// Response:
//
// {
//   id,
//   full_name,
//   email,
//   role,
//   is_active,
//   created_at
// }
//

export const register = async (
  fullName,
  email,
  password
) => {
  const response =
    await api.post(
      '/api/auth/register',
      {
        full_name:
          fullName.trim(),

        email:
          email.trim(),

        password,
      }
    );

  return response.data;
};


// ============================================================
// LOGIN — STEP 1
// ============================================================
//
// POST /api/auth/login
//
// Request:
//
// {
//   email,
//   password
// }
//
// Backend verifies credentials and generates
// login OTP.
//
// JWT is NOT saved here.
//
// JWT should be saved after OTP verification.
//

export const login = async (
  email,
  password
) => {
  const response =
    await api.post(
      '/api/auth/login',
      {
        email:
          email.trim(),

        password,
      }
    );

  return response.data;
};


// ============================================================
// LOGIN — STEP 2
// ============================================================
//
// POST /api/auth/login/verify-otp
//
// Request:
//
// {
//   email,
//   otp
// }
//
// Response:
//
// {
//   access_token,
//   token_type
// }
//

export const verifyLoginOTP = async (
  email,
  otp
) => {
  const response =
    await api.post(
      '/api/auth/login/verify-otp',
      {
        email:
          email.trim(),

        otp:
          String(otp).trim(),
      }
    );

  return response.data;
};


// ============================================================
// CURRENT USER
// ============================================================
//
// GET /api/auth/me
//
// Requires JWT.
//

export const getCurrentUser =
  async () => {
    const response =
      await api.get(
        '/api/auth/me'
      );

    return response.data;
  };


// ============================================================
// FORGOT PASSWORD — STEP 1
// ============================================================
//
// POST /api/auth/forgot-password
//
// Request:
//
// {
//   email
// }
//
// Backend generates password-reset OTP.
//

export const forgotPassword =
  async (
    email
  ) => {
    const response =
      await api.post(
        '/api/auth/forgot-password',
        {
          email:
            email.trim(),
        }
      );

    return response.data;
  };


// ============================================================
// FORGOT PASSWORD — STEP 2
// ============================================================
//
// POST /api/auth/forgot-password/verify-otp
//
// Request:
//
// {
//   email,
//   otp
// }
//
// Response may contain a reset token.
//

export const verifyForgotPasswordOTP =
  async (
    email,
    otp
  ) => {
    const response =
      await api.post(
        '/api/auth/forgot-password/verify-otp',
        {
          email:
            email.trim(),

          otp:
            String(otp).trim(),
        }
      );

    return response.data;
  };


// ============================================================
// RESET PASSWORD
// ============================================================
//
// POST /api/auth/reset-password
//
// Request:
//
// {
//   token,
//   new_password
// }
//

export const resetPassword =
  async (
    token,
    newPassword
  ) => {
    const response =
      await api.post(
        '/api/auth/reset-password',
        {
          token,

          new_password:
            newPassword,
        }
      );

    return response.data;
  };


// ============================================================
// CHANGE PASSWORD
// ============================================================
//
// POST /api/auth/change-password
//
// Requires JWT.
//

export const changePassword =
  async (
    currentPassword,
    newPassword
  ) => {
    const response =
      await api.post(
        '/api/auth/change-password',
        {
          current_password:
            currentPassword,

          new_password:
            newPassword,
        }
      );

    return response.data;
  };


// ============================================================
// PATIENTS
// ============================================================


// ============================================================
// GET ALL PATIENTS
// ============================================================
//
// GET /api/patients
//
// Requires JWT.
//

export const getPatients =
  async () => {
    const response =
      await api.get(
        '/api/patients'
      );

    return response.data;
  };


// ============================================================
// GET SINGLE PATIENT
// ============================================================
//
// GET /api/patients/{patient_id}
//

export const getPatient =
  async (
    patientId
  ) => {
    const response =
      await api.get(
        `/api/patients/${encodeURIComponent(
          patientId
        )}`
      );

    return response.data;
  };


// ============================================================
// CREATE PATIENT
// ============================================================
//
// POST /api/patients
//

export const createPatient =
  async (
    patientData
  ) => {
    const response =
      await api.post(
        '/api/patients',
        patientData
      );

    return response.data;
  };


// ============================================================
// UPDATE PATIENT
// ============================================================
//
// PATCH /api/patients/{patient_id}
//

export const updatePatient =
  async (
    patientId,
    patientData
  ) => {
    const response =
      await api.patch(
        `/api/patients/${encodeURIComponent(
          patientId
        )}`,
        patientData
      );

    return response.data;
  };


// ============================================================
// SCANS
// ============================================================


// ============================================================
// UPLOAD SCAN
// ============================================================
//
// POST /api/scans?patient_id=...
//
// Multipart form-data.
//
// Field:
// file
//

export const uploadScan =
  async (
    patientId,
    file,
    onUploadProgress
  ) => {
    const formData =
      new FormData();

    formData.append(
      'file',
      file
    );

    const response =
      await api.post(
        `/api/scans?patient_id=${encodeURIComponent(
          patientId
        )}`,
        formData,
        {
          onUploadProgress,

          /*
           * AI analysis can take longer
           * than normal API requests.
           */

          timeout: 180000,
        }
      );

    return response.data;
  };


// ============================================================
// GET ALL SCANS
// ============================================================
//
// GET /api/scans
//

export const getScans =
  async () => {
    const response =
      await api.get(
        '/api/scans'
      );

    return response.data;
  };


// ============================================================
// GET PATIENT SCANS
// ============================================================
//
// GET /api/scans/patient/{patient_id}
//

export const getPatientScans =
  async (
    patientId
  ) => {
    const response =
      await api.get(
        `/api/scans/patient/${encodeURIComponent(
          patientId
        )}`
      );

    return response.data;
  };


// ============================================================
// GET SINGLE SCAN
// ============================================================
//
// GET /api/scans/{scan_id}
//

export const getScan =
  async (
    scanId
  ) => {
    const response =
      await api.get(
        `/api/scans/${encodeURIComponent(
          scanId
        )}`
      );

    return response.data;
  };


// ============================================================
// DEFAULT API INSTANCE
// ============================================================

export default api;