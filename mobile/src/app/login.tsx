import { router } from 'expo-router';
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Message } from '@/components/Message';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { userMessage } from '@/utils/errors';

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!identifier.trim() || !password) {
      setError(t('auth.errorRequired'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(identifier.trim(), password);
      router.replace('/');
    } catch (e) {
      setError(userMessage(e, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <TextField
        label={t('auth.identifier')}
        hint={t('auth.identifierHint')}
        value={identifier}
        onChangeText={setIdentifier}
        autoCapitalize="none"
        autoComplete="username"
        keyboardType="email-address"
        textContentType="username"
      />
      <TextField
        label={t('auth.password')}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete="current-password"
        textContentType="password"
        onSubmitEditing={submit}
      />
      <Message text={error} />
      <Button title={t('auth.submitLogin')} onPress={submit} loading={busy} />
      <Button
        title={t('auth.noAccount')}
        variant="ghost"
        onPress={() => router.replace('/register')}
      />
    </Screen>
  );
}
