'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { CheckCircle, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

function AuthSuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    const name = searchParams.get('name');
    const email = searchParams.get('email');

    if (!token) {
      setStatus('error');
      setTimeout(() => {
        router.push('/login?error=auth_failed');
      }, 2000);
      return;
    }

    // Store the token
    api.setToken(token);
    
    // Store user info in localStorage for quick access
    if (name) {
      localStorage.setItem('user_name', name);
      setUserName(name);
    }
    if (email) {
      localStorage.setItem('user_email', email);
    }

    setStatus('success');

    // Redirect to dashboard after short delay
    setTimeout(() => {
      router.push('/dashboard');
    }, 1500);
  }, [searchParams, router]);

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {status === 'processing' && (
            <>
              <Loader2 className="w-16 h-16 text-primary-600 animate-spin mx-auto mb-4" />
              <h1 className="text-xl font-semibold text-gray-900 mb-2">
                Processing...
              </h1>
              <p className="text-gray-600">
                Setting up your account...
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h1 className="text-xl font-semibold text-gray-900 mb-2">
                Welcome{userName ? `, ${userName}` : ''}!
              </h1>
              <p className="text-gray-600">
                Authentication successful. Redirecting to your dashboard...
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">❌</span>
              </div>
              <h1 className="text-xl font-semibold text-gray-900 mb-2">
                Authentication Failed
              </h1>
              <p className="text-gray-600">
                Something went wrong. Redirecting to login...
              </p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

function AuthSuccessFallback() {
  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <Loader2 className="w-16 h-16 text-primary-600 animate-spin mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-gray-900 mb-2">
            Processing...
          </h1>
          <p className="text-gray-600">
            Setting up your account...
          </p>
        </div>
      </div>
    </main>
  );
}

export default function AuthSuccessPage() {
  return (
    <Suspense fallback={<AuthSuccessFallback />}>
      <AuthSuccessContent />
    </Suspense>
  );
}
