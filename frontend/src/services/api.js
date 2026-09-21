import axios from 'axios';


// ============================================================
// API CONFIGURATION
// ============================================================

const getApiBaseUrl = () => {
  const envUrl =
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL;

  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }

  if (import.meta.env.PROD) {
    return 'https://fetalai-backend.onrender.com';
  }

  return 'http://127.0.0.1:8000';
};

export const API_BASE_URL = getApiBaseUrl();


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

export const ERROR_CODE_MESSAGES = {
  VALIDATION_ERROR: 'Please select a valid scan.',
  FILE_TOO_LARGE: 'The selected file exceeds the 15 MB size limit.',
  UNSUPPORTED_FILE_TYPE: 'This file format is not supported.',
  INVALID_IMAGE: 'The uploaded image appears to be invalid or corrupted.',
  INVALID_VTK: 'The VTK 3D mesh appears to be invalid or corrupted.',
  WORKER_DISABLED: 'This analysis model is currently disabled (model unavailable).',
  WORKER_STARTUP_FAILED: 'The AI analysis worker failed to start. Please try again.',
  WORKER_UNAVAILABLE: 'The AI analysis service is temporarily unavailable.',
  INFERENCE_TIMEOUT: 'The analysis took too long. Please try again.',
  WORKER_TIMEOUT: 'The analysis took too long. Please try again.',
  INFERENCE_FAILED: 'The scan could not be analyzed.',
  INTERNAL_ERROR: 'Something went wrong on the server. Please try again.',
};

export const getApiErrorMessage = (
  error,
  fallback = 'Something went wrong. Please try again.'
) => {
  /*
   * Standardized FetalAI Error Envelope:
   *
   * {
   *   "success": false,
   *   "model": "plane",
   *   "error": {
   *     "code": "WORKER_UNAVAILABLE",
   *     "message": "..."
   *   }
   * }
   */
  const structuredError = error?.response?.data?.error;
  if (structuredError) {
    if (typeof structuredError.message === 'string' && structuredError.message.trim()) {
      return structuredError.message.trim();
    }
    if (structuredError.code && ERROR_CODE_MESSAGES[structuredError.code]) {
      return ERROR_CODE_MESSAGES[structuredError.code];
    }
  }

  const detail =
    error?.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }
        return item?.msg || 'Invalid request.';
      })
      .join(', ');
  }

  if (typeof detail === 'string') {
    return detail;
  }

  if (typeof error?.response?.data?.message === 'string') {
    return error.response.data.message;
  }

  if (typeof error?.message === 'string') {
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
// VERIFY SIGNUP OTP
// ============================================================

export const verifySignupOTP = async (
  email,
  otp
) => {
  const response =
    await api.post(
      '/api/auth/register/verify-otp',
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
// RESEND SIGNUP OTP
// ============================================================

export const resendSignupOTP = async (
  email
) => {
  const response =
    await api.post(
      '/api/auth/register/resend-otp',
      {
        email:
          email.trim(),
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
// RESEND LOGIN OTP
// ============================================================

export const resendLoginOTP = async (
  email
) => {
  const response =
    await api.post(
      '/api/auth/login/resend-otp',
      {
        email:
          email.trim(),
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
// RESEND FORGOT PASSWORD OTP
// ============================================================

export const resendForgotPasswordOTP = async (
  email
) => {
  const response =
    await api.post(
      '/api/auth/forgot-password/resend-otp',
      {
        email:
          email.trim(),
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
// MULTI-MODEL INFERENCE API (GATEWAY PORT 8000)
// ============================================================

const _postInference = async (modelName, file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post(
    `/api/v1/inference/${encodeURIComponent(modelName)}`,
    formData,
    {
      onUploadProgress,
      timeout: 180000,
    }
  );

  return response.data;
};

export const predictPlane = async (file, onUploadProgress) => {
  return _postInference('plane', file, onUploadProgress);
};

export const predictSpine = async (file, onUploadProgress) => {
  return _postInference('spine', file, onUploadProgress);
};

export const predictBrain = async (file, onUploadProgress) => {
  return _postInference('brain', file, onUploadProgress);
};

export const predictLung = async (file, onUploadProgress) => {
  return _postInference('lung', file, onUploadProgress);
};

export const predictBone = async (file, onUploadProgress) => {
  return _postInference('bone', file, onUploadProgress);
};

export const predictPlacenta = async (file, onUploadProgress) => {
  return _postInference('placenta', file, onUploadProgress);
};

export const predictFace = async (file, onUploadProgress) => {
  return _postInference('face', file, onUploadProgress);
};

export const predictHeart = async (file, onUploadProgress) => {
  return _postInference('heart', file, onUploadProgress);
};

export const predictComprehensive = async (
  scanSlots = {},
  patientId = null,
  idempotencyKey = null,
  sessionId = null,
  onUploadProgress = null
) => {
  // Support flexible argument positions if progress callback is passed as 3rd arg
  let cb = onUploadProgress;
  let idem = idempotencyKey;
  let sid = sessionId;

  if (typeof idempotencyKey === 'function') {
    cb = idempotencyKey;
    idem = null;
    sid = null;
  }

  const formData = new FormData();
  
  if (scanSlots.plane) formData.append('plane_scan', scanSlots.plane);
  if (scanSlots.spine) formData.append('spine_scan', scanSlots.spine);
  if (scanSlots.brain) formData.append('brain_scan', scanSlots.brain);
  if (scanSlots.lung) formData.append('lung_scan', scanSlots.lung);
  if (scanSlots.bone) formData.append('bone_scan', scanSlots.bone);
  if (scanSlots.placenta) formData.append('placenta_scan', scanSlots.placenta);
  if (scanSlots.face) formData.append('face_mesh', scanSlots.face);
  if (scanSlots.heart) formData.append('heart_scan', scanSlots.heart);
  
  if (patientId) {
    formData.append('patient_id', String(patientId));
  }
  if (idem) {
    formData.append('idempotency_key', String(idem));
  }
  if (sid) {
    formData.append('session_id', String(sid));
  }

  const response = await api.post(
    '/api/v1/inference/comprehensive',
    formData,
    {
      onUploadProgress: cb,
      timeout: 240000,
    }
  );

  return response.data;
};

export const getWorkerStatus = async () => {
  const response = await api.get('/api/v1/inference/workers/status');
  return response.data;
};

export const stopWorker = async (modelName) => {
  const response = await api.post(`/api/v1/inference/workers/${encodeURIComponent(modelName)}/stop`);
  return response.data;
};


// ============================================================
// ANALYSIS SESSIONS API
// ============================================================

export const createAnalysisSession = async (payload) => {
  const response = await api.post('/api/v1/analysis/sessions', payload);
  return response.data?.data || response.data;
};

export const getAnalysisSessions = async (params = {}) => {
  const response = await api.get('/api/v1/analysis/sessions', { params });
  return response.data?.data || response.data;
};

export const getAnalysisSession = async (sessionId) => {
  const response = await api.get(`/api/v1/analysis/sessions/${encodeURIComponent(sessionId)}`);
  return response.data?.data || response.data;
};

export const retryAnalysisSession = async (sessionId) => {
  const response = await api.post(`/api/v1/analysis/sessions/${encodeURIComponent(sessionId)}/retry`);
  return response.data?.data || response.data;
};


// ============================================================
// REPORTS & PDF EXPORT API
// ============================================================

export const getReports = async (params = {}) => {
  const response = await api.get('/api/v1/reports', { params });
  return response.data?.data || response.data;
};

export const getReport = async (reportIdOrNumber) => {
  const response = await api.get(`/api/v1/reports/${encodeURIComponent(reportIdOrNumber)}`);
  return response.data?.data || response.data;
};

export const getReportPdfBlob = async (reportIdOrNumber) => {
  const response = await api.get(`/api/v1/reports/${encodeURIComponent(reportIdOrNumber)}/pdf`, {
    responseType: 'blob',
    timeout: 60000,
  });
  return response.data;
};

export const downloadReportPdf = async (reportIdOrNumber, filename = null) => {
  const blob = await getReportPdfBlob(reportIdOrNumber);
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename || `${reportIdOrNumber}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
};

export const archiveReport = async (reportIdOrNumber) => {
  const response = await api.post(`/api/v1/reports/${encodeURIComponent(reportIdOrNumber)}/archive`);
  return response.data;
};

export const createReport = async (reportData) => {
  const response = await api.post('/api/v1/reports', reportData);
  return response.data;
};


// ============================================================
// DEFAULT API INSTANCE
// ============================================================

export default api;
