import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000';

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

    if (token) {
      config.headers =
        config.headers || {};

      config.headers.Authorization =
        `Bearer ${token}`;
    }

    return config;
  },
  (error) =>
    Promise.reject(error)
);


// ============================================================
// RESPONSE INTERCEPTOR
// ============================================================

api.interceptors.response.use(
  (response) => response,

  (error) => {

    if (
      error.response?.status === 401
    ) {

      console.warn(
        'Authentication failed: 401 Unauthorized'
      );

      // Remove invalid / expired token.
      localStorage.removeItem(
        'access_token'
      );

      // AuthContext / application
      // can handle the redirect.
    }

    return Promise.reject(error);
  }
);


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

export const login = async (
  email,
  password
) => {

  const response =
    await api.post(
      '/api/auth/login',
      {
        email,
        password,
      }
    );

  return response.data;
};


// ============================================================
// FORGOT PASSWORD
// ============================================================

export const forgotPassword = async (
  email
) => {

  const response =
    await api.post(
      '/api/auth/forgot-password',
      {
        email,
      }
    );

  return response.data;
};


// ============================================================
// RESET PASSWORD
// ============================================================

export const resetPassword = async (
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

export const changePassword = async (
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
// CURRENT USER
// ============================================================

export const getCurrentUser =
  async () => {

    const response =
      await api.get(
        '/api/auth/me'
      );

    return response.data;
  };


// ============================================================
// PATIENTS
// ============================================================

export const getPatients =
  async () => {

    const response =
      await api.get(
        '/api/patients'
      );

    return response.data;
  };


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
          timeout: 180000,
        }
      );

    return response.data;
  };


export const getScans =
  async () => {

    const response =
      await api.get(
        '/api/scans'
      );

    return response.data;
  };


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