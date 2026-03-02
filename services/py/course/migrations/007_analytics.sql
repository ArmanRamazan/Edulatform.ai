CREATE OR REPLACE VIEW course_analytics AS
SELECT
    c.id AS course_id,
    c.teacher_id,
    c.title,
    c.avg_rating,
    c.review_count,
    COUNT(DISTINCT m.id) AS module_count,
    COUNT(DISTINCT l.id) AS lesson_count
FROM courses c
LEFT JOIN modules m ON m.course_id = c.id
LEFT JOIN lessons l ON l.module_id = m.id
GROUP BY c.id, c.teacher_id, c.title, c.avg_rating, c.review_count;
