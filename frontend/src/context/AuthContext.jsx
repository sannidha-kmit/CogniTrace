import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('cognitrace_token'));
  const [loading, setLoading] = useState(true);

  // Restore authenticated session on initial mount or token change
  useEffect(() => {
    const restoreSession = async () => {
      const storedToken = localStorage.getItem('cognitrace_token');
      if (!storedToken) {
        setUser(null);
        setToken(null);
        setLoading(false);
        return;
      }

      try {
        const res = await fetch('/api/v1/auth/me', {
          headers: {
            'Authorization': `Bearer ${storedToken}`
          }
        });

        if (res.ok) {
          const userData = await res.json();
          setUser(userData);
          setToken(storedToken);
        } else {
          // Token invalid or expired
          localStorage.removeItem('cognitrace_token');
          setUser(null);
          setToken(null);
        }
      } catch (err) {
        console.error('Session restore failed:', err);
        localStorage.removeItem('cognitrace_token');
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);

  const login = async (identifier, password) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.message || 'Login failed. Please check credentials.');
    }

    localStorage.setItem('cognitrace_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const registerStudent = async (studentData) => {
    const res = await fetch('/api/v1/auth/register/student', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(studentData)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.message || 'Student registration failed.');
    }

    localStorage.setItem('cognitrace_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const registerTeacher = async (teacherData) => {
    const res = await fetch('/api/v1/auth/register/teacher', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(teacherData)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.message || 'Teacher registration failed.');
    }

    localStorage.setItem('cognitrace_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    if (token) {
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } catch (err) {
        console.warn('Logout notification request failed:', err);
      }
    }
    localStorage.removeItem('cognitrace_token');
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      registerStudent,
      registerTeacher,
      logout
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
