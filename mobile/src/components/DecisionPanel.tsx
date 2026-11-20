/**
 * The verifier's three actions (FR 2.1, FR 2.2):
 *   Confirm             -> asks "are you sure?" first
 *   Reject              -> needs a reason (one-tap options or typed)
 *   Flag as duplicate   -> needs a reason
 * The reason is shown to the reporter, so it is kept short and plain.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import { QUICK_REASONS, type ReasonAction, cleanReason, isValidReason } from '@/review/decision';
import { colors, font, radius, spacing } from '@/theme';

import { Button } from './Button';
import { ChipRow } from './ChipRow';
import { TextField } from './TextField';

interface Props {
  busy: boolean;
  onConfirm: () => void;
  onReason: (action: ReasonAction, reason: string) => void;
}

export function DecisionPanel({ busy, onConfirm, onReason }: Props) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<ReasonAction | null>(null);
  const [reason, setReason] = useState('');

  if (mode === null) {
    return (
      <View style={styles.actions}>
        <Button
          testID="decide-confirm"
          title={t('review.confirm')}
          icon="checkmark-circle"
          onPress={onConfirm}
          loading={busy}
        />
        <Button
          testID="decide-reject"
          title={t('review.reject')}
          icon="close-circle"
          variant="danger"
          onPress={() => setMode('reject')}
          disabled={busy}
        />
        <Button
          testID="decide-flag"
          title={t('review.flag')}
          icon="flag"
          variant="secondary"
          onPress={() => setMode('flag')}
          disabled={busy}
        />
      </View>
    );
  }

  const valid = isValidReason(reason);
  return (
    <View style={styles.form} testID={`reason-form-${mode}`}>
      <Text style={styles.title}>{t(mode === 'reject' ? 'review.rejectTitle' : 'review.flagTitle')}</Text>
      <Text style={styles.hint}>{t('review.reasonHint')}</Text>
      <View style={styles.quick}>
        <ChipRow
          wrap
          chips={QUICK_REASONS[mode].map((key) => ({ value: t(key), label: t(key) }))}
          selected={cleanReason(reason)}
          onSelect={setReason}
          testIDPrefix="quick-reason"
        />
      </View>
      <TextField
        testID="reason-input"
        label={t('review.reasonLabel')}
        value={reason}
        onChangeText={setReason}
        multiline
        maxLength={500}
      />
      {!valid && reason.length > 0 ? <Text style={styles.error}>{t('review.needReason')}</Text> : null}
      <Button
        testID="reason-submit"
        title={t(mode === 'reject' ? 'review.submitReject' : 'review.submitFlag')}
        variant={mode === 'reject' ? 'danger' : 'primary'}
        onPress={() => onReason(mode, cleanReason(reason))}
        disabled={!valid}
        loading={busy}
      />
      <Button
        title={t('common.cancel')}
        variant="ghost"
        onPress={() => {
          setMode(null);
          setReason('');
        }}
        disabled={busy}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  actions: { gap: spacing.sm },
  form: {
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { fontSize: font.large, fontWeight: '700', color: colors.text },
  hint: { fontSize: font.body, color: colors.textMuted },
  quick: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  error: { fontSize: font.small, color: colors.danger },
});
