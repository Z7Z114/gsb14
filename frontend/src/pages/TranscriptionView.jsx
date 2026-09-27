import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Box, Typography, Button, Card, CardContent, Chip } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';

function TranscriptionView() {
  const { id } = useParams();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    fetch(`/api/audio/recordings/${id}/transcriptions`)
      .then(res => res.json())
      .then(data => setRows(Array.isArray(data) ? data : []))
      .catch(err => console.error('Failed to fetch transcriptions:', err));
  }, [id]);

  return (
    <Box>
      <Button component={Link} to="/detectors" startIcon={<ArrowBack />} sx={{ mb: 2 }}>返回</Button>
      <Typography variant="h4" gutterBottom>录音转写</Typography>
      <Card>
        <CardContent>
          {rows.map((row) => (
            <Box key={row.id} sx={{ mb: 2 }}>
              <Typography variant="subtitle2">
                [{row.speaker_role}] {row.speaker} · {row.start_time}s-{row.end_time}s
              </Typography>
              <Typography variant="body1">{row.text}</Typography>
              <Box sx={{ mt: 1 }}>
                {(row.physics_terms || []).map((t, i) => (
                  <Chip key={i} size="small" label={t} sx={{ mr: 1, mb: 1 }} />
                ))}
              </Box>
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  );
}

export default TranscriptionView;
