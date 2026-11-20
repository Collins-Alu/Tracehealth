import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Message } from '@/components/Message';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { colors, font, radius, spacing } from '@/theme';
import { userMessage } from '@/utils/errors';

function Checkbox({
  checked,
  onToggle,
  label,
  testID,
}: {
  checked: boolean;
  onToggle: () => void;
  label: string;
  testID?: string;
}) {
  return (
    <Pressable
      testID={testID}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      onPress={onToggle}
      style={styles.checkRow}
    >
      <Ionicons
        name={checked ? 'checkmark-circle' : 'ellipse-outline'}
        size={28}
        color={colors.primary}
      />
      <Text style={styles.checkLabel}>{label}</Text>
    </Pressable>
  );
}

export default function Register() {
  const { t, i18n } = useTranslation();
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [acceptPrivacy, setAcceptPrivacy] = useState(false);
  const [payoutConsent, setPayoutConsent] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!fullName.trim() || !phone.trim() || !password) {
      setError(t('auth.errorRequired'));
      return;
    }
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError(t('auth.errorPasswordRule'));
      return;
    }
    if (!acceptPrivacy) {
      setError(t('auth.errorPrivacy'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await register({
        full_name: fullName.trim(),
        phone_number: phone.trim(),
        email: email.trim() || undefined,
        password,
        preferred_language: i18n.language === 'sw' ? 'SW' : 'EN',
        accept_privacy_notice: true,
        payout_consent: payoutConsent,
      });
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
        label={t('auth.fullName')}
        value={fullName}
        onChangeText={setFullName}
        autoComplete="name"
      />
      <TextField
        label={t('auth.phone')}
        hint={t('auth.identifierHint')}
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
        autoComplete="tel"
      />
      <TextField
        label={`${t('auth.email')} (${t('common.optional')})`}
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
      />
      <TextField
        label={t('auth.password')}
        hint={t('auth.passwordHint')}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete="new-password"
      />
      <View style={styles.privacy}>
        <Text style={styles.privacyTitle}>{t('auth.privacyTitle')}</Text>
        <Text style={styles.privacyText}>{t('auth.privacyText')}</Text>
      </View>
      <Checkbox
        testID="accept-privacy"
        checked={acceptPrivacy}
        onToggle={() => setAcceptPrivacy((v) => !v)}
        label={t('auth.acceptPrivacy')}
      />
      <Checkbox
        checked={payoutConsent}
        onToggle={() => setPayoutConsent((v) => !v)}
        label={t('auth.payoutConsent')}
      />
      <Message text={error} />
      <Button title={t('auth.submitRegister')} onPress={submit} loading={busy} />
      <Button title={t('auth.haveAccount')} variant="ghost" onPress={() => router.replace('/login')} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  privacy: {
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.primarySoft,
    gap: spacing.xs,
  },
  privacyTitle: { fontSize: font.body, fontWeight: '700', color: colors.primaryDark },
  privacyText: { fontSize: font.body, color: colors.text, lineHeight: 22 },
  checkRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, minHeight: 48 },
  checkLabel: { flex: 1, fontSize: font.body, color: colors.text },
});
