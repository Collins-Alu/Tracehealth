/**
 * Create a pollution report (Module 2, UML B.3 steps 1–2).
 *
 *   Step 1  Photo      camera or gallery, with the safety reminder
 *   Step 2  Location   GPS is requested as soon as the screen opens
 *   Step 3  Category   one of the five SRS categories
 *   Step 4  Details    optional description, review, send
 *
 * Sending saves the report in the offline queue first, then tries to upload
 * it straight away. The confirmation screen says whether it was sent or is
 * waiting for a connection.
 */
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { router } from 'expo-router';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Image, Linking, StyleSheet, Text, View } from 'react-native';

import type { PollutionCategory } from '@/api/types';
import { Button } from '@/components/Button';
import { CategoryPicker } from '@/components/CategoryPicker';
import { Message } from '@/components/Message';
import { SafetyNotice } from '@/components/SafetyNotice';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { SUBMIT_WAIT_MS } from '@/config';
import { useSync } from '@/offline/SyncContext';
import { colors, font, radius, spacing } from '@/theme';
import { formatCoords } from '@/utils/format';

const TOTAL_STEPS = 4;
const GPS_TIMEOUT_MS = 15_000;
const POOR_ACCURACY_M = 100;
const LAST_KNOWN_MAX_AGE_MS = 10 * 60 * 1000;

interface Fix {
  latitude: number;
  longitude: number;
  accuracyM: number | null;
  lastKnown: boolean;
}

type LocationState =
  | { kind: 'locating' }
  | { kind: 'found'; fix: Fix }
  | { kind: 'error'; reason: 'denied' | 'servicesOff' | 'failed' };

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => setTimeout(() => reject(new Error('timeout')), ms)),
  ]);
}

export default function NewReport() {
  const { t } = useTranslation();
  const { enqueue, sendSoon } = useSync();
  const [step, setStep] = useState(1);
  const [photo, setPhoto] = useState<{ uri: string; capturedAt: string } | null>(null);
  const [location, setLocation] = useState<LocationState>({ kind: 'locating' });
  const [category, setCategory] = useState<PollutionCategory | null>(null);
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const mounted = useRef(true);

  const locate = useCallback(async () => {
    setLocation({ kind: 'locating' });
    const { granted } = await Location.requestForegroundPermissionsAsync();
    if (!granted) return mounted.current && setLocation({ kind: 'error', reason: 'denied' });
    if (!(await Location.hasServicesEnabledAsync())) {
      return mounted.current && setLocation({ kind: 'error', reason: 'servicesOff' });
    }
    try {
      const pos = await withTimeout(
        Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
        GPS_TIMEOUT_MS,
      );
      if (!mounted.current) return;
      setLocation({
        kind: 'found',
        fix: {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracyM: pos.coords.accuracy ?? null,
          lastKnown: false,
        },
      });
    } catch {
      const last = await Location.getLastKnownPositionAsync({ maxAge: LAST_KNOWN_MAX_AGE_MS });
      if (!mounted.current) return;
      setLocation(
        last
          ? {
              kind: 'found',
              fix: {
                latitude: last.coords.latitude,
                longitude: last.coords.longitude,
                accuracyM: last.coords.accuracy ?? null,
                lastKnown: true,
              },
            }
          : { kind: 'error', reason: 'failed' },
      );
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    locate(); // start GPS while the user takes the photo
    return () => {
      mounted.current = false;
    };
  }, [locate]);

  async function pickPhoto(source: 'camera' | 'gallery') {
    setError(null);
    try {
      if (source === 'camera') {
        const { granted } = await ImagePicker.requestCameraPermissionsAsync();
        if (!granted) return setError(t('newReport.cameraDenied'));
      }
      const options: ImagePicker.ImagePickerOptions = {
        mediaTypes: ['images'],
        quality: 0.6, // smaller uploads on slow networks; the server resizes again
        exif: false,
        allowsEditing: false,
      };
      const result =
        source === 'camera'
          ? await ImagePicker.launchCameraAsync(options)
          : await ImagePicker.launchImageLibraryAsync(options);
      if (!result.canceled && result.assets[0]) {
        setPhoto({ uri: result.assets[0].uri, capturedAt: new Date().toISOString() });
      }
    } catch {
      setError(source === 'camera' ? t('newReport.cameraDenied') : t('newReport.galleryDenied'));
    }
  }

  function next() {
    setError(null);
    if (step === 1 && !photo) return setError(t('newReport.needPhoto'));
    if (step === 2 && location.kind !== 'found') return setError(t('newReport.needLocation'));
    if (step === 3 && !category) return setError(t('newReport.needCategory'));
    setStep((s) => Math.min(s + 1, TOTAL_STEPS));
  }

  function back() {
    setError(null);
    if (step === 1) router.back();
    else setStep((s) => s - 1);
  }

  async function submit() {
    if (busy || !photo || location.kind !== 'found' || !category) return;
    setBusy(true);
    setError(null);
    try {
      const id = await enqueue({
        photoUri: photo.uri,
        category,
        latitude: location.fix.latitude,
        longitude: location.fix.longitude,
        accuracyM: location.fix.accuracyM,
        description: description.trim() || null,
        capturedAt: photo.capturedAt,
      });
      const result = await sendSoon(id, SUBMIT_WAIT_MS);
      router.replace({ pathname: '/submitted', params: { result } });
    } catch {
      setError(t('newReport.saveFailed'));
      setBusy(false);
    }
  }

  const footer = (
    <View style={styles.footerRow}>
      <View style={{ flex: 1 }}>
        <Button title={t('common.back')} variant="secondary" onPress={back} disabled={busy} />
      </View>
      <View style={{ flex: 1.4 }}>
        {step < TOTAL_STEPS ? (
          <Button title={t('common.continue')} onPress={next} testID="next" />
        ) : (
          <Button
            title={busy ? t('newReport.submitting') : t('newReport.submit')}
            icon="checkmark-circle"
            onPress={submit}
            loading={busy}
            testID="submit"
          />
        )}
      </View>
    </View>
  );

  return (
    <Screen footer={footer}>
      <Text style={styles.stepLabel}>{t('newReport.stepOf', { step, total: TOTAL_STEPS })}</Text>

      {step === 1 && (
        <>
          <Text style={styles.title}>{t('newReport.photoTitle')}</Text>
          <SafetyNotice />
          {photo ? (
            <Image source={{ uri: photo.uri }} style={styles.photo} accessibilityIgnoresInvertColors />
          ) : null}
          <Button
            title={photo ? t('newReport.retakePhoto') : t('newReport.takePhoto')}
            icon="camera"
            onPress={() => pickPhoto('camera')}
          />
          <Button
            title={t('newReport.choosePhoto')}
            icon="images"
            variant="secondary"
            onPress={() => pickPhoto('gallery')}
          />
        </>
      )}

      {step === 2 && (
        <>
          <Text style={styles.title}>{t('newReport.locationTitle')}</Text>
          <LocationPanel state={location} />
          {location.kind === 'error' && location.reason === 'denied' ? (
            <Button
              title={t('newReport.openSettings')}
              variant="secondary"
              onPress={() => Linking.openSettings()}
            />
          ) : null}
          <Button
            title={t('newReport.updateLocation')}
            icon="location"
            variant="secondary"
            onPress={locate}
            disabled={location.kind === 'locating'}
          />
        </>
      )}

      {step === 3 && (
        <>
          <Text style={styles.title}>{t('newReport.categoryTitle')}</Text>
          <CategoryPicker value={category} onChange={setCategory} />
        </>
      )}

      {step === 4 && photo && location.kind === 'found' && category && (
        <>
          <Text style={styles.title}>{t('newReport.reviewTitle')}</Text>
          <TextField
            label={`${t('newReport.descriptionLabel')} (${t('common.optional')})`}
            placeholder={t('newReport.descriptionPlaceholder')}
            value={description}
            onChangeText={setDescription}
            multiline
            maxLength={1000}
          />
          <View style={styles.review}>
            <Image source={{ uri: photo.uri }} style={styles.thumb} />
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={styles.reviewTitle}>{t(`categories.${category}`)}</Text>
              <Text style={styles.reviewMeta}>
                {formatCoords(location.fix.latitude, location.fix.longitude)}
              </Text>
            </View>
          </View>
        </>
      )}

      <Message text={error} />
    </Screen>
  );
}

function LocationPanel({ state }: { state: LocationState }) {
  const { t } = useTranslation();
  if (state.kind === 'locating') return <Message tone="info" text={t('newReport.locating')} />;
  if (state.kind === 'error') {
    const key = {
      denied: 'newReport.locationDenied',
      servicesOff: 'newReport.locationServicesOff',
      failed: 'newReport.locationFailed',
    }[state.reason];
    return <Message text={t(key)} />;
  }
  const { fix } = state;
  return (
    <View style={styles.locationCard} testID="location-found">
      <Text style={styles.reviewTitle}>{t('newReport.locationFound')}</Text>
      <Text style={styles.coords}>{formatCoords(fix.latitude, fix.longitude)}</Text>
      {fix.accuracyM != null ? (
        <Text style={styles.reviewMeta}>
          {t('newReport.accuracy', { meters: Math.round(fix.accuracyM) })}
        </Text>
      ) : null}
      {fix.lastKnown ? <Text style={styles.warn}>{t('newReport.lastKnown')}</Text> : null}
      {fix.accuracyM != null && fix.accuracyM > POOR_ACCURACY_M ? (
        <Text style={styles.warn}>{t('newReport.accuracyPoor')}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  stepLabel: { fontSize: font.small, color: colors.textMuted, fontWeight: '600' },
  title: { fontSize: font.title, fontWeight: '800', color: colors.text },
  photo: { width: '100%', aspectRatio: 4 / 3, borderRadius: radius.md, backgroundColor: colors.border },
  footerRow: { flexDirection: 'row', gap: spacing.sm },
  locationCard: {
    padding: spacing.md,
    gap: spacing.xs,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  coords: { fontSize: font.large, color: colors.text, fontVariant: ['tabular-nums'] },
  warn: { fontSize: font.body, color: colors.warning },
  review: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  thumb: { width: 80, height: 80, borderRadius: radius.sm },
  reviewTitle: { fontSize: font.large, fontWeight: '700', color: colors.text },
  reviewMeta: { fontSize: font.body, color: colors.textMuted },
});
