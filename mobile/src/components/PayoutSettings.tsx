/**
 * Reporter reward settings (D4): agree to rewards by mobile money and choose
 * the number. Nobody is paid without this agreement; withdrawing it stops
 * future payouts. Changing it needs a connection, because it is checked and
 * recorded by the server.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, Switch, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { colors, font, radius, spacing } from '@/theme';
import { userMessage } from '@/utils/errors';

import { Button } from './Button';
import { Message } from './Message';
import { TextField } from './TextField';

export function PayoutSettings() {
  const { t } = useTranslation();
  const { user, updateProfile } = useAuth();
  const consented = !!user?.payout_phone;
  const [wantsRewards, setWantsRewards] = useState(consented);
  const [phone, setPhone] = useState(user?.payout_phone ?? '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; tone: 'error' | 'info' } | null>(null);

  if (!user?.roles.includes('REPORTER')) return null;

  async function save(consent: boolean) {
    setBusy(true);
    setMessage(null);
    try {
      const fresh = await updateProfile(
        consent ? { payout_consent: true, ...(phone.trim() ? { payout_phone: phone.trim() } : {}) } : { payout_consent: false },
      );
      setPhone(fresh.payout_phone ?? '');
      setWantsRewards(!!fresh.payout_phone);
      setMessage({ text: t('account.payoutSaved'), tone: 'info' });
    } catch (error) {
      setMessage({ text: userMessage(error, t), tone: 'error' });
    } finally {
      setBusy(false);
    }
  }

  function onToggle(value: boolean) {
    setMessage(null);
    if (!value && consented) {
      Alert.alert(t('account.payoutStop'), t('account.payoutStopConfirm'), [
        { text: t('common.cancel'), style: 'cancel' },
        { text: t('account.payoutStop'), style: 'destructive', onPress: () => save(false) },
      ]);
      return;
    }
    setWantsRewards(value);
  }

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{t('account.payoutTitle')}</Text>
      <Text style={styles.body} testID="payout-status">
        {consented ? t('account.payoutOn', { phone: user.payout_phone }) : t('account.payoutOff')}
      </Text>
      <View style={styles.switchRow}>
        <Text style={styles.switchLabel}>{t('account.payoutConsent')}</Text>
        <Switch
          testID="payout-consent"
          accessibilityLabel={t('account.payoutConsent')}
          value={wantsRewards}
          onValueChange={onToggle}
          disabled={busy}
          trackColor={{ true: colors.primary, false: colors.border }}
        />
      </View>
      {wantsRewards ? (
        <>
          <TextField
            label={t('account.payoutPhone')}
            hint={t('account.payoutPhoneHint')}
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            autoComplete="tel"
            placeholder={user.phone_number}
            testID="payout-phone"
          />
          <Button title={t('account.payoutSave')} icon="cash" onPress={() => save(true)} loading={busy} testID="payout-save" />
        </>
      ) : null}
      <Message text={message?.text ?? null} tone={message?.tone} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: spacing.md,
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { fontSize: font.body, fontWeight: '700', color: colors.text },
  body: { fontSize: font.body, color: colors.textMuted, lineHeight: 22 },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.md },
  switchLabel: { flex: 1, fontSize: font.body, color: colors.text },
});
